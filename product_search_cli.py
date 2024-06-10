import logging
import os
from pathlib import Path
import sys
from typing import Tuple

from dotenv import load_dotenv
import numpy as np
from PIL.Image import Image

load_dotenv()

from utils.google_cloud import get_similar_products, VISION_CLIENT, ANNOTATION_CLIENT
from utils.image import (
    get_pil_image_from_uri,
    draw_bounding_boxes_on_image,
    save_image_as_png,
    encode_image_as_png_str
)


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s %(levelname)s:%(message)s"
    )
logger = logging.getLogger(__name__)


PROJECT_ID = os.environ.get("PROJECT_ID")
PROJECT_REGION = os.environ.get("PROJECT_REGION")



def get_relevant_products(
    image_uri: str = None,
    image_src: Image = None
    ) -> Tuple[Image, dict]:
    pil_image = image_uri and get_pil_image_from_uri(image_uri=image_uri) or image_src
    image_bytes = encode_image_as_png_str(pil_image)
    results = get_similar_products(
        search_client=VISION_CLIENT,
        annotation_client=ANNOTATION_CLIENT,
        project_id=PROJECT_ID,
        location=PROJECT_REGION,
        product_set_id="bahag_products",
        product_category="homegoods-v2",
        image=image_bytes
        )
    
    bboxes = np.array([bbox["vertices"] for bbox in results["bboxes"]])
    captions =[
        [bbox["annotations"].pop()]
        for bbox in results["bboxes"]
        if bbox["annotations"] or ""
        ]
    draw_bounding_boxes_on_image(
        pil_image,
        boxes=bboxes,
        display_str_list_list=captions,
        color="green",
        thickness=2
        )
    return pil_image, results["matches"]
        

if __name__ == "__main__":
    input_img_uri = sys.argv[1]
    try:
        annotated_image, matches = get_relevant_products(image_uri=input_img_uri)
        save_image_as_png(annotated_image, Path("output.png"))
        print(matches, file=sys.stdout)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
