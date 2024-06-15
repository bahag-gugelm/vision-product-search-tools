import logging
import os
from typing import IO

from google.api_core import exceptions
from google.api_core.retry import Retry
from google.cloud import storage, vision

_RETRIABLE_TYPES = [
    exceptions.TooManyRequests,  # 429
    exceptions.InternalServerError,  # 500
    exceptions.BadGateway,  # 502
    exceptions.ServiceUnavailable,  # 503
]


def is_retryable(exc):
    return isinstance(exc, _RETRIABLE_TYPES)


RETRY_POLICY = Retry(predicate=is_retryable)


GCP_SA_JSON = os.environ.get("GCP_SA_JSON")

if GCP_SA_JSON:
    GCS_CLIENT = storage.Client.from_service_account_json(GCP_SA_JSON)
    VISION_CLIENT = vision.ProductSearchClient.from_service_account_json(GCP_SA_JSON)
    ANNOTATION_CLIENT = vision.ImageAnnotatorClient.from_service_account_json(GCP_SA_JSON)
else:
    GCS_CLIENT = storage.Client()
    VISION_CLIENT = vision.ProductSearchClient()
    ANNOTATION_CLIENT = vision.ImageAnnotatorClient()


logger = logging.getLogger(__name__)


def upload_to_storage(
    client: storage.Client,
    bucket_id: str,
    file: IO,
    remote_fname: str,
):
    bucket = client.bucket(bucket_id)
    blob = bucket.blob(remote_fname)
    blob.upload_from_file(file, timeout=1800, retry=RETRY_POLICY)
    logger.info(f"Uploaded {remote_fname} to the storage bucket.")
    return f"gs://{bucket_id}/{remote_fname}"


# almost reference implementation from the docs
# https://cloud.google.com/vision/product-search/docs/create-product-set
def bulk_import_product_sets(
    client: vision.ProductSearchClient, project_id: str, location: str, csv_bulk_gcs_uri: str = "gs://"
):
    """Import images of different products in the product set.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        csv_bulk_gcs_uri: Google Cloud Storage URI.
            Target files must be in Product Search CSV format.
    """

    # A resource that represents Google Cloud Platform location.
    location_path = f"projects/{project_id}/locations/{location}"

    # Set the input configuration along with Google Cloud Storage URI
    gcs_source = vision.ImportProductSetsGcsSource(csv_file_uri=csv_bulk_gcs_uri)
    input_config = vision.ImportProductSetsInputConfig(gcs_source=gcs_source)

    # Import the product sets from the input URI.
    response = client.import_product_sets(parent=location_path, input_config=input_config, timeout=1800, retry=RETRY_POLICY)

    logger.info(f"Processing operation name: {response.operation.name}")
    # synchronous check of operation status
    result = response.result()

    for idx, status in enumerate(result.statuses):
        # Check the status of reference image
        # `0` is the code for OK in google.rpc.Code.
        if status.code == 0:
            reference_image = result.reference_images[idx]
            logger.info(f"Indexed entry {idx}, {reference_image}")
        else:
            logger.warning(f"Status code not OK: {status.message}")

    logger.info(f"Processing done. Indexed {csv_bulk_gcs_uri}")


def get_similar_products(
    search_client: vision.ProductSearchClient,
    annotation_client: vision.ImageAnnotatorClient,
    project_id: str,
    location: str,
    product_set_id: str,
    product_category: str,
    image: bytes,
    _filter: str = "",
    max_results: int = 10,
) -> dict:
    """Search similar products to image.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        product_category: Category of the product.
        image: Byte string of image to be searched.
        _filter: Condition to be applied on the labels.
        Example for _filter: (color = red OR color = blue) AND style = kids
        It will search on all products with the following labels:
        color:red AND style:kids
        color:blue AND style:kids
        max_results: The maximum number of results (matches) to return.
    """

    image = vision.Image(content=image)

    # product search specific parameters
    product_set_path = search_client.product_set_path(project=project_id, location=location, product_set=product_set_id)
    product_search_params = vision.ProductSearchParams(
        product_set=product_set_path,
        product_categories=[product_category],
        filter=_filter,
    )
    image_context = vision.ImageContext(product_search_params=product_search_params)

    # Search products similar to the image.
    response = annotation_client.product_search(image, image_context=image_context, max_results=max_results)
    results = response.product_search_results.product_grouped_results

    if not results:
        logger.info(response.error.message)

    output = {"bboxes": [], "matches": {}}

    for idx, result in enumerate(results, 1):
        annotations = [f"{idx} - {ann.name} / {ann.score:.4f}" for ann in result.object_annotations]
        obj_bb, matches = result.bounding_poly, result.results
        vertices = obj_bb.normalized_vertices
        xs, ys = [vertex.x for vertex in vertices], [vertex.y for vertex in vertices]
        min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)
        output["bboxes"].append({"vertices": [min_y, min_x, max_y, max_x], "annotations": annotations})
        match_key = f"object {idx}"
        output["matches"][match_key] = list()
        for match in matches:
            product = match.product
            output["matches"][match_key].append(
                {
                    "score": f"{match.score:.4f}",
                    "product": f"https://www.bauhaus.info/p/{product.name.split('/').pop()}",
                }
            )

    return output


def list_product_sets(project_id: str, location: str, client: vision.ProductSearchClient):
    """List all product sets.
    Args:
        project_id: Id of the project.
        location: A compute region name.
    """
    # A resource that represents Google Cloud Platform location.
    location_path = f"projects/{project_id}/locations/{location}"

    # List all the product sets available in the region.
    product_sets = client.list_product_sets(parent=location_path)
    # Display the product set information.
    for product_set in product_sets:
        logger.info(f"Product set name: {product_set.name}")
        logger.info(f"Product set id: {product_set.name.split('/').pop()}")
        logger.info(f"Product set display name: {product_set.display_name}")
        logger.info(f"Product set index time: {product_set.index_time}")


def purge_products_in_product_set(
    project_id: str, location: str, product_set_id: str, client: vision.ProductSearchClient, force: bool
):
    """Delete all products in a product set.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
        force: Perform the purge only when force is set to True.
    """

    parent = f"projects/{project_id}/locations/{location}"

    product_set_purge_config = vision.ProductSetPurgeConfig(product_set_id=product_set_id)

    # The purge operation is async.
    operation = client.purge_products(
        request={
            "parent": parent,
            "product_set_purge_config": product_set_purge_config,
            # The operation is irreversible and removes multiple products.
            # The user is required to pass in force=True to actually perform the
            # purge. If force is not set to True, the service raises an exception.
            "force": force,
        },
        timeout=1800,
        retry=RETRY_POLICY
    )

    logger.info("Deleted products in product set.")


def delete_product_set(project_id: str, location: str, client: vision.ProductSearchClient, product_set_id: str):
    """Delete a product set.
    Args:
        project_id: Id of the project.
        location: A compute region name.
        product_set_id: Id of the product set.
    """
    # Get the full path of the product set.
    product_set_path = client.product_set_path(project=project_id, location=location, product_set=product_set_id)

    # Delete the product set.
    client.delete_product_set(name=product_set_path, timeout=1800, retry=RETRY_POLICY)
    logger.info("Product set deleted.")
