import logging
import os
import sys

from dotenv import load_dotenv
from google.cloud import vision
from utils.google_cloud import purge_products_in_product_set, delete_product_set


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


if __name__ == "__main__":
    product_set = sys.argv[1]
    ur = input(f"You're about to delete the product set: {product_set}. Are you sure?\n")
    if ur in ("YES", "yes", "y", "Y"):
        logger.info(f"Purging all products in {product_set}")
        purge_products_in_product_set(
            project_id=PROJECT_ID,
            location=PROJECT_REGION,
            client=VISION_CLIENT,
            product_set_id=product_set,
            force=True
            )
        logger.info(f"Deleting {product_set}")
        delete_product_set(
            project_id=PROJECT_ID,
            location=PROJECT_REGION,
            client=VISION_CLIENT,
            product_set_id=product_set
        )
