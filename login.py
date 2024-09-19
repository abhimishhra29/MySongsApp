from flask import Flask, render_template, request, redirect, session
from boto3.dynamodb.conditions import Key, Attr  # Import Attr function
import requests
import boto3

app = Flask(__name__)
app.secret_key = 's3934581'  # Change this to a secure random value in production

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('login')
music_table = dynamodb.Table('Music')  # Assuming 'Music' is the name of your DynamoDB table
subscribe_table = dynamodb.Table('subscribe')  # New table for subscribed music
register_api_gateway_endpoint = 'https://5b7e54f6la.execute-api.us-east-1.amazonaws.com/Production/register_function'
subscribe_API_Gateway_endpoint = 'https://01rrfdnf0m.execute-api.us-east-1.amazonaws.com/Production/subscribe_function'
remove_API_Gateway_endpoint = "https://638x5lts85.execute-api.us-east-1.amazonaws.com/Production/remove_function"


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # Query DynamoDB for user credentials
    response = table.query(
        KeyConditionExpression=Key('email').eq(email)
    )

    # Retrieve items from the response
    items = response.get('Items')

    # Check if any item is found
    if items:
        # For now, let's assume there's only one item
        user = items[0]

        # Check if the password matches
        if user.get('password') == password:
            # Set user session
            session['user_email'] = email
            session['user_name'] = user.get('user_name')  # Store the username in session
            return redirect('/dashboard')
        else:
            error_msg = 'Invalid credentials. Please try again.'
            return render_template('login.html', error=error_msg)
    else:
        error_msg = 'User not found.'
        return render_template('login.html', error=error_msg)


@app.route('/dashboard')
def dashboard():
    if 'user_email' in session:
        user_name = session.get('user_name')  # Retrieve the username from session
        user_email = session['user_email']

        # Fetch subscribed music items from DynamoDB
        try:
            response = subscribe_table.query(
                KeyConditionExpression=Key('email').eq(user_email)
            )
            subscribed_music = response.get('Items', [])

            # Fetch image URLs for subscribed music items
            for item in subscribed_music:
                try:
                    # Get the pre-signed URL for the image
                    url = s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': 's3934581-a1',
                                                             'Key': f'{item["artist"]}.jpg'},
                                                     ExpiresIn=3600)
                    item['image_url'] = url
                except Exception as e:
                    print(f"Error fetching image URL for {item['artist']}: {e}")
        except Exception as e:
            return f"Error fetching subscribed music: {e}", 500

        # Extract parameters from the request
        artist = request.args.get('artist')
        title = request.args.get('title')
        year = request.args.get('year')

        # Convert 'year' to integer if provided
        if year:
            year = int(year)

        # Initialize the FilterExpression
        filter_expr = None

        # Check if any parameter is provided
        if artist or title or year:
            # Initialize the list to hold the conditions
            conditions = []

            # Add conditions for artist, title, and year if provided
            if artist:
                conditions.append(Attr('artist').eq(artist))
            if title:
                conditions.append(Attr('title').eq(title))
            if year:
                conditions.append(Attr('year').eq(year))

            # Construct the FilterExpression using logical AND operator
            filter_expr = conditions[0]
            for condition in conditions[1:]:
                filter_expr &= condition

        # Scan the Music table with the constructed FilterExpression
        if filter_expr:
            response = music_table.scan(
                FilterExpression=filter_expr
            )

            # Extract music items from the response
            music_items = response.get('Items', [])
            print(music_items)
        else:
            # If no parameters provided, return an empty list of music items
            music_items = []

        # Fetch image URLs from S3 and add them to music items
        for item in music_items:
            try:
                # Get the pre-signed URL for the image
                url = s3_client.generate_presigned_url('get_object',
                                                           Params={'Bucket': 's3937821task2',
                                                                   'Key': f'{item["artist"]}.jpg'},
                                                           ExpiresIn=3600)

                item['image_url'] = url
            except Exception as e:
                print(f"Error fetching image URL for {item['artist']}: {e}")

        # Render the dashboard template with the user's email, username, and retrieved music items
        return render_template('dashboard.html', email=session['user_email'], user_name=user_name, music_items=music_items, subscribed_music=subscribed_music)
    else:
        # If user is not logged in, redirect to login page
        return redirect('/')


@app.route('/subscribe', methods=['POST'])
def subscribe():
    # Check if the user is logged in
    if 'user_email' in session:
        user_email = session['user_email']
        title = request.form.get('title')
        artist = request.form.get('artist')
        year = request.form.get('year')
        image_url = request.form.get('image_url')

        # Send a POST request to the API Gateway endpoint
        try:
            response = requests.post(subscribe_API_Gateway_endpoint, json={'user_email': user_email, 'title': title, 'artist': artist, 'year': year, 'image_url': image_url})
            print(response)
            data = response.json()
            print(data)
            if 'statusCode' in data and data['statusCode'] == 200:
                return redirect('/dashboard')
            else:
                return f"Error subscribing: {data['body']}", 500
        except Exception as e:
            return f"Error subscribing: {e}", 500
    else:
        # If user is not logged in, redirect to login page
        return redirect('/')


@app.route('/remove', methods=['POST'])
def remove():
    # Check if the user is logged in
    if 'user_email' in session:
        user_email = session['user_email']
        title = request.form.get('title')
        print(user_email, title)
        # Send a POST request to the API Gateway endpoint
        try:
            response = requests.post(remove_API_Gateway_endpoint, json={'user_email': user_email, 'title': title})
            print(response)
            data = response.json()

            if 'statusCode' in data and data['statusCode'] == 200:
                return redirect('/dashboard')
            else:
                return f"Error removing subscription: {data['body']}", 500
        except Exception as e:
            return f"Error removing subscription: {e}", 500
    else:
        # If user is not logged in, redirect to login page
        return redirect('/')


@app.route('/logout')
def logout():
    session.pop('user_email', None)
    session.pop('user_name', None)  # Remove the username from session
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Invoke the Lambda function via API Gateway
        try:
            response = requests.post(register_api_gateway_endpoint, json={'email': email, 'username': username, 'password': password})
            data = response.json()

            if 'statusCode' in data and data['statusCode'] == 200:
                # User registered successfully
                return redirect('/')  # Redirect to login page
            if 'statusCode' in data and data['statusCode'] == 400:
                # Registration failed (user already exists)
                error_msg = "User with this email already exists."
                return render_template('register.html', error=error_msg)
            else:
                # Other error occurred
                error_msg = data.get('errorMessage', 'Unknown error')
                return render_template('register.html', error=error_msg)
        except Exception as e:
            return render_template('register.html', error=str(e))
    else:
        return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)
