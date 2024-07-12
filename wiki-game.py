from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import urllib.parse

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wikipedia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the database model
class WikipediaPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WikipediaPage {self.title}>'

# Function to fetch a random Wikipedia page
def get_random_wikipedia_page():
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnlimit": 1,
        "rnnamespace": 0
    }
    response = requests.get(url, params=params)
    data = response.json()
    page_id = data['query']['random'][0]['id']
    page_title = data['query']['random'][0]['title']
    return page_id, page_title

# Function to fetch the summary of a Wikipedia page and limit to first 10 lines
def get_wikipedia_summary(page_id):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "pageids": page_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    page = data['query']['pages'][str(page_id)]
    summary = page['extract']

    # Limit summary to the first 10 lines
    summary_lines = summary.split('\n')[:10]
    truncated_summary = '\n'.join(summary_lines)
    
    return truncated_summary

# Function to fetch or retrieve from database
def fetch_or_get_from_db(page_id, page_title):
    # Check if the page is already in the database
    page = WikipediaPage.query.filter_by(page_id=page_id).first()
    if page and page.timestamp > datetime.utcnow() - timedelta(days=1):
        # If the page is in the database and it's recent, return it
        return page

    # If the page is not in the database or it's old, fetch new data
    summary = get_wikipedia_summary(page_id)
    new_page = WikipediaPage(page_id=page_id, title=page_title, summary=summary)

    # Save the new page to the database
    db.session.add(new_page)
    db.session.commit()

    return new_page

# Route to fetch two random Wikipedia topics
@app.route('/api/topics')
def fetch_two_random_topics():
    try:
        # Fetch two random Wikipedia pages
        page1_id, page1_title = get_random_wikipedia_page()
        page2_id, page2_title = get_random_wikipedia_page()

        # Fetch or retrieve from database
        page1 = fetch_or_get_from_db(page1_id, page1_title)
        page2 = fetch_or_get_from_db(page2_id, page2_title)

        # Generate URLs for each topic
        base_url = "https://en.wikipedia.org/wiki/"
        url1 = base_url + urllib.parse.quote(page1_title.replace(" ", "_"))
        url2 = base_url + urllib.parse.quote(page2_title.replace(" ", "_"))

        # Return JSON response with URLs and truncated summaries
        return jsonify({
            'topic1': {'title': page1.title, 'summary': page1.summary[:1000], 'url': url1},
            'topic2': {'title': page2.title, 'summary': page2.summary[:1000], 'url': url2}
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Route to render the HTML template
@app.route('/')
def index():
    return render_template('index.html')

#if __name__ == "__main__":
#    with app.app_context():
#        db.create_all()  # Create database tables if they do not exist
#    app.run(debug=True, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables if they do not exist
    app.run(debug=True, host='0.0.0.0', port=8080)
