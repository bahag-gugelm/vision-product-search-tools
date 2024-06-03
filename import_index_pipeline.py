import os
import logging
import time
import sys

from dotenv import load_dotenv

load_dotenv()

from google.cloud import vision
from google.cloud import storage

from import_assets import run_job as prepare_bulk_import, OUT_DIR
from utils.google_cloud import bulk_import_product_sets, upload_to_storage


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )
logger = logging.getLogger(__name__)


GCP_SA_JSON = os.environ.get("GCP_SA_JSON")
PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")
BULK_CSV_BUCKET_ID = os.environ.get("BULK_CSV_BUCKET_ID", "vision-product-search-csv")

GCS_CLIENT = storage.Client.from_service_account_json(GCP_SA_JSON)
VISION_CLIENT = vision.ProductSearchClient.from_service_account_json(GCP_SA_JSON)


if __name__ == "__main__":
    logger.info("Starting import and indexing pipeline. Getting assets.")
    try:
        prepare_bulk_import()
        logger.info("Assets saved and bulk import files prepared. Starting indexing job.")
        for fpath in OUT_DIR.glob("*.csv"):
            remote_csv_uri = upload_to_storage(
                bucket_id=BULK_CSV_BUCKET_ID,
                client=GCS_CLIENT,
                file=fpath.open(encoding="utf8"),
                remote_fname=fpath.name
                )
            bulk_import_product_sets(
                client=VISION_CLIENT,
                project_id=PROJECT_ID,
                location=PROJECT_REGION,
                csv_bulk_gcs_uri=remote_csv_uri
                )
            time.sleep(10)
        logger.info("Done, it's a success!")
    except Exception as e:
        logger.exception(f"Job run has failed because of {str(e)}")
        sys.exit(1)