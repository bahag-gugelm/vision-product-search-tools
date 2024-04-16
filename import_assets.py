from io import BytesIO
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage

import psycopg2

from utils.assets_api import BahagAssetsAPI
from utils.google_cloud import upload_to_storage
from utils.output import RotatingTextWriter


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )
logger = logging.getLogger(__name__)


load_dotenv()


N_THREADS = os.cpu_count() * 2

POSTGRES_SERVER = os.environ.get("POSTGRES_SERVER")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
BAHAG_BASE_API_URL = os.environ.get("BAHAG_BASE_API_URL")
ASSETS_API_USER = os.environ.get("ASSETS_API_USER")
ASSETS_API_PASSWORD = os.environ.get("ASSETS_API_PASSWORD")

GCP_SA_JSON = os.environ.get("GCP_SA_JSON")

STORAGE_BUCKET_ID = os.environ.get("STORAGE_BUCKET_ID")
GCS_CLIENT = storage.Client.from_service_account_json(GCP_SA_JSON)

MEDIA_TYPE = ("IMAGE_JPG", )

OUT_DIR = Path(__file__).parent / "OUTPUT"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV_FILE = OUT_DIR / "product_vision_bulk_import.csv"
OUT_MOOD_SHOTS_FILE = OUT_DIR / "test_mood_shots.out"

# https://cloud.google.com/vision/product-search/docs/csv-format
LINES_PER_OUT_FILE = 20_000

PRODUCT_SET = "bahag_products"


def db_connect():
    conn = psycopg2.connect(
        host=POSTGRES_SERVER,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
        )
    return conn
    

def get_bahag_products(batch_size: int = 10_000, page: int = 1):
    logger.info(f"Getting products with batch size: {batch_size}")
    with db_connect().cursor() as cur:
        while True:
            skip = (page - 1) * batch_size
            sql = f'SELECT q205."Variant_product" FROM "PIM_query20_5" q205 LIMIT {batch_size} OFFSET {skip};'
            cur.execute(query=sql)
            result_set = cur.fetchall()
            if not result_set:
                break
            yield list(sum(result_set, ()))
            logger.info(f"Fetched {skip + len(result_set)} items")
            page += 1


def get_assets_info(
    client: BahagAssetsAPI,
    bahag_id: str,
    country_code: str = "de",
    language_id: str = "de-DE"
    ):
    api_data = client.get_assets_data(
        bahag_id=bahag_id,
        country_code=country_code,
        language_id=language_id
        )
    
    if not api_data:
        return
    
    result = {
        "product_id": api_data["sap_number"],
        "images": []
        }
    
    for item in api_data["result"]:
        if item["type"] == "PRODUCT_IMAGE":
            asset_data = item["asset"]
            for img in asset_data["image_derivatives"]:
                if img["media_type"] in MEDIA_TYPE and img["name"] == "prod_large_square":
                    result["images"].append(
                        {
                            "type": "_".join(asset_data["sub_type"].lower().split()),
                            "url": img["url"]
                            }
                        )
    return result
                

def process(assets_client: BahagAssetsAPI, bahag_id: str):
    item_assets = get_assets_info(client=assets_client, bahag_id=bahag_id)
    if not item_assets:
        logger.warning(f"No API data for id={bahag_id}")
        return
    # process only items with mood shots to save them and later use as test data
    has_mood_shots = any([img["type"] == "mood_shot" for img in item_assets["images"]])

    if not item_assets["images"]:
        logger.warning(f"No assets for id={bahag_id}")
        return
    
    if not has_mood_shots:
        logger.warning(f"No mood shots for id={bahag_id}")
        return
    
    result = {"bulk_entries": [], "moodshot_entries": []}

    for asset in item_assets["images"]:
        asset_url = asset["url"]
        asset_type = asset["type"]
        
        if not asset_url:
            logger.warning(f"No url for id={bahag_id}, type={asset_type}")
            continue
        
        if asset_type == "mood_shot":
            ms_entry = f"{bahag_id},{asset_url}\n"
            result["moodshot_entries"].append(ms_entry)
            continue
            
        file_data = assets_client.get_asset_file(asset_url)
        
        if not file_data:
            continue
        
        filename, filesize, content = file_data
            
        if filesize >= 1024 * 1024 * 20:
            logger.warning(f"File too big (>20MB) for id={bahag_id}, url: {asset_url}")
            continue
        
        bucket_filename = f"{bahag_id}_{asset_type}_{filename}"
        gcs_url = upload_to_storage(
            client=GCS_CLIENT,
            bucket_id=STORAGE_BUCKET_ID,
            file=BytesIO(content),
            remote_fname=bucket_filename
            )
        
        bulk_entry = (
            gcs_url, "", PRODUCT_SET, bahag_id,
            "homegoods-v2", "bahag_product", f"\"type={asset_type}\"", ""
            )
        
        result["bulk_entries"].append(f"{','.join(bulk_entry)}\n")
        
        return result


def run_job():
    total_count = 0
    processed_count = 0
    with BahagAssetsAPI(
        user=ASSETS_API_USER,
        password=ASSETS_API_PASSWORD,
        base_url=BAHAG_BASE_API_URL
        ) as assets_client:
        with RotatingTextWriter(OUT_CSV_FILE, max_lines=LINES_PER_OUT_FILE) as bulk_file:
            with OUT_MOOD_SHOTS_FILE.open(mode="at", newline="") as ms_file:
                for batch in get_bahag_products():
                    total_count += len(batch)
                    with ThreadPoolExecutor(max_workers=N_THREADS) as pool:
                        futures = (pool.submit(process, assets_client, bahag_id) for bahag_id in batch)
                        for future in as_completed(futures):
                            result = future.result()
                            for bulk_entry in result["bulk_entries"]:
                                bulk_file.write(bulk_entry)
                            for mood_shot_entry in result["moodshot_entries"]:
                                ms_file.write(mood_shot_entry)
                            
                            processed_count += 1
                
    logger.info(
        f"Done, saved {processed_count} suitable items out of {total_count} in total,\n"
        f"{bulk_file.total_lines_written} rows written in {bulk_file.rollover_count + 1} files."
        )


if __name__ == "__main__":
    run_job()