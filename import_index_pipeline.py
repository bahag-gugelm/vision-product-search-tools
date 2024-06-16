import logging
import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from import_assets import OUT_DIR  # noqa: E402
from import_assets import run_job as prepare_bulk_import  # noqa: E402
from utils.google_cloud import GCS_CLIENT, VISION_CLIENT, bulk_import_product_sets, upload_to_storage  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(name)s - %(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

# setup in Dockerfile
LOGFILE_PATH = Path("import_index_pipeline.log")

PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")
BULK_CSV_BUCKET_ID = os.environ.get("BULK_CSV_BUCKET_ID", "vision-product-search-csv")


if __name__ == "__main__":
    logger.info("Starting import and indexing pipeline. Getting assets.")
    try:
        prepare_bulk_import()
        logger.info("Assets saved and bulk import files prepared. Starting indexing job.")
        files_to_index = list()
        for fpath in OUT_DIR.glob("*.csv"):
            remote_csv_uri = upload_to_storage(
                bucket_id=BULK_CSV_BUCKET_ID,
                client=GCS_CLIENT,
                file=fpath.open(encoding="utf8"),
                remote_fname=fpath.name,
            )
            files_to_index.append(remote_csv_uri)
        
        for remote_csv in files_to_index:
            bulk_import_product_sets(
                client=VISION_CLIENT, project_id=PROJECT_ID, location=PROJECT_REGION, csv_bulk_gcs_uri=remote_csv
            )
            time.sleep(10)
        logger.info("Done, it's a success!")
    except Exception as e:
        logger.exception(f"Job run has failed because of {str(e)}")
        sys.exit(1)
    finally:
        if LOGFILE_PATH.exists():
            logger.info(f"Uploading job log file to {BULK_CSV_BUCKET_ID}")
            upload_to_storage(
                bucket_id=BULK_CSV_BUCKET_ID,
                client=GCS_CLIENT,
                file=LOGFILE_PATH.open(encoding="utf8"),
                remote_fname=LOGFILE_PATH.name,
                )
