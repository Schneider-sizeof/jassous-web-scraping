from flask import Flask, render_template, request, jsonify, send_file, make_response
from collections import Counter
import requests
import os
import re
import zipfile
import json
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import nltk
from flask import send_file

app = Flask(__name__)

# Folder to store images temporarily
IMAGE_FOLDER = 'images_temp'
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)
@app.route('/download_data', methods=['POST'])
def download_data():
    try:
        data_type = request.form.get('data_type')
        url = request.form.get('url')

        if not data_type or not url:
            return jsonify({"error": "Missing data type or URL."}), 400

        if data_type == "links":
            data = scrape_links(url)
            filename = "links.json"
        elif data_type == "keywords":
            data = scrape_keywords(url)
            # Convert keywords to a list of dictionaries for JSON compatibility
            data = [{"keyword": k, "count": v} for k, v in data]
            filename = "keywords.json"
        else:
            return jsonify({"error": "Invalid data type."}), 400

        # Create JSON response
        response = make_response(json.dumps(data, indent=4))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"

        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if not url or not url.startswith(('http://', 'https://')):
            return jsonify({"error": "Invalid or missing URL. Ensure it starts with 'http://' or 'https://'."})
        
        data_type = request.form.get('data_type')

        try:
            if data_type == "images":
                images = scrape_images(url)
                return render_template('result_images.html', images=images, url=url)
            elif data_type == "links":
                links = scrape_links(url)
                return render_template('result_links.html', links=links)
            elif data_type == "keywords":
                keywords = scrape_keywords(url)
                keyword_count = len(keywords)
                return render_template('result_keywords.html', keywords=keywords, count=keyword_count)
            else:
                return jsonify({"error": "Invalid data type selected!"})
        except Exception as e:
            return jsonify({"error": str(e)})

    return render_template('index.html')
# Function to scrape links
def scrape_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = []

    for link in soup.find_all('a', href=True):
        full_url = requests.compat.urljoin(url, link['href'])  # Resolve relative links
        links.append(full_url)

    # Add enumeration here
    return list(enumerate(links, start=1))  # Enumerate with index starting at 1

# Function to scrape keywords (meta keywords)
def scrape_keywords(url):
    try:
        # Get the page content
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all the text from the page
        text = soup.get_text()

        # Normalize the text: remove punctuation and convert to lowercase
        text = re.sub(r'\W+', ' ', text.lower())

        # Split the text into words
        words = text.split()

        # Remove stopwords (common words like "the", "and", etc.)
        stop_words = set(stopwords.words('english'))
        words = [word for word in words if word not in stop_words]

        # Count word frequency using Counter
        word_counts = Counter(words)

        # Get the most common 10 words
        common_keywords = word_counts.most_common(20)

        print(f"Most frequent words: {common_keywords}")  # Debugging line
        return common_keywords

    except Exception as e:
        print(f"Error scraping keywords: {e}")  # Debugging line
        return []

def scrape_images(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    images = []

    for img in soup.find_all('img'):
        img_url = img.get('src')
        if img_url:
            if not img_url.startswith('https://'):  # Handle relative URLs
                img_url = requests.compat.urljoin(url, img_url)
            images.append(img_url)

    return images

@app.route('/download_images', methods=['POST'])
def download_images():
    url = request.form.get('url')

    # Scrape images
    images = scrape_images(url)

    # Create a temporary directory to store the images
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

    # Download and save all images in the directory
    for i, img_url in enumerate(images):
        try:
            img_data = requests.get(img_url).content
            img_name = os.path.join(IMAGE_FOLDER, f"image_{i+1}.jpg")  # default .jpg if extension not found
            with open(img_name, 'wb') as f:
                f.write(img_data)
        except Exception as e:
            print(f"Error downloading image {i+1}: {e}")

    # Create a zip file containing all the images
    zip_filename = 'images.zip'
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(IMAGE_FOLDER):
            for file in files:
                zipf.write(os.path.join(root, file), file)

    # Clean up the images folder after zipping
    for root, _, files in os.walk(IMAGE_FOLDER):
        for file in files:
            os.remove(os.path.join(root, file))

    # Send the zip file for download
    return send_file(zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
