import os
from google import genai
from google.genai import types

def main():
    client = genai.Client()
    
    # List of images to upload
    images = [
        "c:/Users/Meet Sutariya/.gemini/antigravity-ide/brain/3b16b31f-808b-4037-97ec-7da68e00b2a6/builderr_sample_site_home_1788427545770.png",
        "c:/Users/Meet Sutariya/.gemini/antigravity-ide/brain/3b16b31f-808b-4037-97ec-7da68e00b2a6/builderr_sample_site_details_1788427561890.png",
        "c:/Users/Meet Sutariya/.gemini/antigravity-ide/brain/3b16b31f-808b-4037-97ec-7da68e00b2a6/builderr_sample_site_bottom_1788427575245.png",
        "c:/Users/Meet Sutariya/.gemini/antigravity-ide/brain/3b16b31f-808b-4037-97ec-7da68e00b2a6/builderr_sample_site_footprint_1788427590414.png"
    ]
    
    uploaded_files = []
    for img_path in images:
        if os.path.exists(img_path):
            print(f"Uploading {img_path}")
            f = client.files.upload(file=img_path)
            uploaded_files.append(f)
        else:
            print(f"File not found: {img_path}")

    prompt = """
    These are screenshots from the 'Builderr' reference frontend that the user wants to mimic.
    Analyze them deeply. What features, UI components, data points, or interactions are visible here?
    List every single specific element (e.g. 'Search bar with a magnifying glass icon and placeholder text', 'A button that says Export CSV', 'A tabbed interface with Financials, Leadership, and Overview', 'A gauge chart for the Signalpost Score', etc).
    Be extremely comprehensive so I can make sure my HTML/JS implements every single one.
    """

    print("Generating analysis...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=uploaded_files + [prompt]
    )
    
    print("\n--- ANALYSIS ---")
    print(response.text)

if __name__ == "__main__":
    main()
