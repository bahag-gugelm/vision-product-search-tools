# Reverse image product search utils

### Set of tools for managing product sets, indexing and searhing the Google Vision API for the bahag products similar to ones from an input image


Implements the functionality from: https://cloud.google.com/vision/product-search/docs/

---
Additional docs: https://cloud.google.com/solutions/retail?hl=en#google-cloud-for-retail, https://cloud.google.com/vision/docs/object-localizer

#### Usage:

`import_assets.py` gets all the assets for all the bahag products, saves them into a gcs bucket and writes a .csv file for bulk indexing.

`vision_bulk_index.py gs://gsc-bucket/bulk_import_file.csv` imports and indexes all the reference images from a given bulk file.

`list_product_sets.py` lists all the product sets in the project's Vision API instance.

`import_index_pipeline.py` runs the entire import and index all assets pipeline (import assets -> prepare reference images & bulk index *.csv files -> bulk index) 

`delete_product_set.py set_name` deletes the given product set with all the reference images from the Vision API (not the physical files in the bucket).

`product_search_cli.py` searches for products similar to the one found at input URL.

`product_search_ui.py` launches a [gradio](https://www.gradio.app/) UI (browser search app).