import logging
import os
import sys

from dotenv import load_dotenv
from google.cloud import vision

from utils.google_cloud import bulk_import_product_sets


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )
logger = logging.getLogger(__name__)


load_dotenv()


GCP_SA_JSON = os.environ.get("GCP_SA_JSON")
PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")

VISION_CLIENT = vision.ProductSearchClient.from_service_account_json(GCP_SA_JSON)


# first arg is the bulk import csv-file gs location URI inside the project
# gs://vision-product-search-csv/product_vision_bulk_import.csv
if __name__ == "__main__":
    bulk_gcs_uri = sys.argv[1]
    try:
        bulk_import_product_sets(
            client=VISION_CLIENT,
            project_id=PROJECT_ID,
            location=PROJECT_REGION,
            csv_bulk_gcs_uri=bulk_gcs_uri
            )
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
