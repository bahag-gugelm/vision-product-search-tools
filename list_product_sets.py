import logging
import os

from dotenv import load_dotenv

load_dotenv()

from utils.google_cloud import list_product_sets, VISION_CLIENT


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )


PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")



if __name__ == "__main__":
    list_product_sets(
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        client=VISION_CLIENT
        )
