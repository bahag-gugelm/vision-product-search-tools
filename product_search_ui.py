from typing import Tuple

import gradio as gr
from PIL.Image import Image

from product_search_cli import get_relevant_products


def match_image(image_uri: str = None, image_src: Image = None) -> Tuple[Image, str]:
    try:
        annotated_image, matches = get_relevant_products(image_uri, image_src)
    except Exception as e:
        return None, "Nothing found :/"

    output = list()
    for match_obj in matches.keys():
        matched_products = []
        for match in matches[match_obj]:
            matched_products.append(
                f"[{match['product'].split('/').pop()}]({match['product']}) (score: {match['score']})",
            )
        output.append(f"### {match_obj} matches:\n\n" + " ∙ ".join(matched_products))

    return annotated_image, "\n".join(output)


if __name__ == "__main__":
    # gradio Interface
    ui = gr.Interface(
        title="Mood Shots Reverse Product Image Search",
        description="Google Cloud Vision API demo",
        fn=match_image,
        inputs=[gr.Textbox(label="Input Image URI"), gr.Image(label="Input Image", type="pil")],
        outputs=[gr.Image(label="Annotated Image"), gr.Markdown(label="Relevant Products")],
    )
    ui.launch()
