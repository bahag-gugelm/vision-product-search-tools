import logging
import os

from dotenv import load_dotenv
from google.cloud import vision
from utils.google_cloud import list_product_sets


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )


load_dotenv()


GCP_SA_JSON = os.environ.get("GCP_SA_JSON")
PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")

VISION_CLIENT = vision.ProductSearchClient.from_service_account_json(GCP_SA_JSON)


if __name__ == "__main__":
    list_product_sets(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        client=VISION_CLIENT
        )
