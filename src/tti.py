from pathlib import Path

from google.genai import Client
from google.genai.types import GenerateImagesConfig

from tools import load_google_api_key

_DEFAULT_MODEL = "models/imagen-4.0-generate-001"


class TTI:
    def __init__(self):
        self.imagen = Client(api_key=load_google_api_key())
        self.model = _DEFAULT_MODEL

    def generate(self, prompt: str, output_file: Path | str):
        """
        Generate flashcard image for the word details.

        Checks if the image already exists on disk before generating.
        If the image file exists, skips generation.

        Args:
            details: The word details to generate an image for
        """

        if isinstance(output_file, str):
            output_file = Path(output_file)

        # Check if image already exists
        if output_file.exists():
            print(f"Image file already exists at {output_file} - skipping generation")
            return

        # Generate new image
        print(f"Generating new image for '{prompt}'")

        result = self.imagen.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1",
                image_size="1K",
            ),
        )

        if not result.generated_images:
            print("No images generated.")
            return

        if len(result.generated_images) != 1:
            print("Number of images generated does not match the requested number.")

        for _, generated_image in enumerate(result.generated_images):
            if generated_image.image is None:
                continue
            generated_image.image.save(str(output_file))
            return


if __name__ == "__main__":
    tti = TTI()
    tti.generate(
        """A student is sitting at a desk in their bedroom. The desk is neat, with an open textbook, a notebook, and a pen. The student is looking at the textbook and taking notes, preparing for a future class. A calendar on the wall has a circle around 'tomorrow's lesson'.

Generate the image as a colourful illustration, with minimal amount of details. Make sure that the background is not white. Make sure that the image fills all complete square, without corner radius.
""",
        "sample.jpg",
    )
