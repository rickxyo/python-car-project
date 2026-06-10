# Project Overview

This application is a car inventory management platform built with Python and Django. The platform provides full create, read, update, and delete operations for car records, user authentication functionality, and automatic description generation using the Google Gemini API.

# Deployment Status

The AWS EC2 instance previously available at http://<ec2-public-ip>/ has been taken offline to avoid ongoing infrastructure costs. The deployment configuration documented in this README file accurately reflects the production setup that was active during development and remains fully reproducible by following the local setup instructions.

# Architecture and System Design

The application architecture consists of a multi-tier setup that integrates a reverse proxy server, an application server, the Django application framework, and a database.

Plain-text diagram of the request flow:

```
Client (Browser) 
      │ (HTTP/HTTPS)
      ▼
Nginx (Reverse Proxy on AWS EC2)
      │ (Unix Socket: python-car-project.sock)
      ▼
uWSGI (Application Server)
      │ (WSGI Interface)
      ▼
Django App (Python Application)
      ├── Brand / Car Models (PostgreSQL Database)
      └── ai_api Client (Gemini API Integration)
```

The components interact in the following sequence:

* Client Request: The client initiates an HTTP or HTTPS request to the application.
* Nginx: Nginx acts as the entry point on the server. Nginx terminates client connections, handles SSL/TLS termination directly, serves static assets directly from the local disk, and forwards dynamic requests.
* Unix Socket: Communication between Nginx and uWSGI occurs through a Unix socket file located at `/var/www/python-car-project/python-car-project.sock`.
* uWSGI: The uWSGI application server receives the forwarded request. It spawns and manages ten worker processes under a master process as configured in `python-car-project.ini`. It executes the Django application code via the Web Server Gateway Interface.
* Django Application: The Django web framework routes the request to the appropriate class-based view. The view queries or updates the PostgreSQL database and renders the user interface.
* Database: PostgreSQL stores application records, including car attributes, brand associations, login session logs, and auto-generated inventory summaries.

# Gemini AI Integration

The system uses Gemini AI to generate factual marketing descriptions for registered cars when no description is supplied by the user.

* Integration Mechanism: The integration is triggered inside the `car_pre_save` signal receiver located in `cars/signals.py`.
* Execution Flow: When a car record is saved, the receiver checks whether the description field is blank or contains only whitespace. If no description exists, the receiver calls the `get_car_ai_description` function from `ai_api/client.py`.
* API Communication: The function invokes the `google-genai` SDK to communicate with the Gemini API. It instantiates the client with a configured API key and queries the designated model, which defaults to `gemini-2.5-flash-lite`.
* Rationale for Design Choices:
  * Automating description generation via database signals ensures consistency. Descriptions are populated whether a car is added through the frontend form, the Django admin panel, database fixtures, or custom command scripts.
  * Encapsulating the integration in the `ai_api` package separates third-party API concerns from standard Django application logic.
  * Checking for existing descriptions before calling the API protects user input and prevents unnecessary, costly external API requests.
  * Restricting model generation settings, such as using a maximum output token limit of 120 and a low temperature of 0.4, ensures concise and predictable outputs suited for inventory listings.

# Technical Tradeoffs

The development of this project involved key design and structural decisions:

* uWSGI over Gunicorn:
  The deployment is configured to use uWSGI instead of Gunicorn. While Gunicorn is simpler to configure and deploy, uWSGI offers a wider range of tuning options, advanced process management capability, and native socket configuration optimizations. The tradeoff is that the configuration syntax is more verbose and requires deep understanding of server parameters to prevent misconfiguration.
* Unix Sockets over TCP Sockets:
  Nginx communicates with uWSGI using a Unix socket located on the local filesystem rather than a TCP port. This bypasses the overhead of the TCP/IP network stack on the localhost loopback interface, reducing communication latency and CPU utilization on the server. The tradeoff is that both Nginx and uWSGI must reside on the same physical or virtual server, which restricts scaling the web server and the application server onto separate machines.
* Synchronous Database Signals for API Requests:
  Calling the Gemini API synchronously inside the pre-save signal simplifies the save flow and guarantees that the description is populated before the database commit completes. The tradeoff is that the save transaction is blocked until the external HTTP request returns. If the Gemini API experiences network delays or outages, database operations will hang, which can exhaust available database connection pools under high traffic. An asynchronous task queue system (such as Celery) would resolve this but would increase overall infrastructure complexity.

# Local Setup and Requirements

Follow these steps to set up and run the application locally:

## System Requirements

* Python 3.10
* PostgreSQL database instance running locally or on a reachable server
* A valid Gemini API key

## Installation Steps

1. Clone the project repository and navigate into the root directory:
   ```bash
   git clone <repository_url>
   cd python-car-project
   ```

2. Create and activate a Python virtual environment:
   On Windows:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
   On macOS or Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables by creating a `.env` file in the root directory. You can copy the template from `.env.example`:
   ```
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   GEMINI_API_KEY=your-gemini-api-key
   GEMINI_MODEL=gemini-2.5-flash-lite
   GEMINI_TRUST_ENV=False
   DB_NAME=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

5. Apply the database migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser account to access the administration interface:
   ```bash
   python manage.py createsuperuser
   ```

7. Launch the local development server:
   ```bash
   python manage.py runserver
   ```
   The application is accessible at `http://127.0.0.1:8000/`.

# Deployment Overview

The application was deployed on an AWS EC2 instance and structured for performance:

* Web Server: Nginx acted as the reverse proxy, accepting incoming HTTP and HTTPS traffic. It was configured to route dynamic traffic directly to the application server and handle client connection scaling. SSL/TLS termination was handled directly by Nginx.
* Application Server: uWSGI served the Django application. It was configured via `python-car-project.ini` to run in master mode with ten processes. The socket permissions were set to 666, allowing seamless socket communication with Nginx.
* Static and Media Files: Static assets were collected into `/var/www/python-car-project/static/` and served directly by Nginx from the local disk. Uploaded media assets were stored under `/var/www/python-car-project/media/` and served directly by Nginx from the local disk.
* Database: A PostgreSQL database instance was hosted directly on the same EC2 instance.
* Server Configuration Management: The server deployment configuration resided within `/var/www/python-car-project`, using standard systemd services to manage the uWSGI process lifecycle.

# Project Structure

```
python-car-project/
├── .env.example             # Template file for environment variable configuration.
├── .gitignore               # Patterns to exclude files from git tracking.
├── LICENSE                  # MIT software license.
├── db.sqlite3               # SQLite database file used during development.
├── manage.py                # Django administrative command-line tool.
├── python-car-project.ini   # uWSGI configuration file for server deployment.
├── requirements.txt         # List of Python package dependencies.
├── uwsgi_params             # Configuration parameters for Nginx-to-uWSGI routing.
├── accounts/                # Django application managing authentication.
│   ├── __init__.py          # Initialization file for the accounts Python package.
│   ├── admin.py             # Django admin panel declarations.
│   ├── apps.py              # Configuration class for the accounts app.
│   ├── models.py            # Empty database models.
│   ├── tests.py             # Test suite files.
│   ├── views.py             # Views managing login, logout, and registration.
│   ├── migrations/          # Database migrations for the accounts app.
│   │   ├── __init__.py      # Initialization file for the migrations package.
│   └── templates/           # HTML templates for user accounts.
│       ├── login.html       # User login page template.
│       └── register.html    # User registration page template.
├── ai_api/                  # Package managing communication with Gemini AI API.
│   ├── __init__.py          # Initialization file for the ai_api Python package.
│   └── client.py            # Client wrapper functions for google-genai SDK.
├── app/                     # Project configuration and entry point directory.
│   ├── __init__.py          # Initialization file for the app Python package.
│   ├── asgi.py              # ASGI entry point for asynchronous servers.
│   ├── settings.py          # Django project settings (loads .env and configures DB).
│   ├── urls.py              # Main URL routing configuration.
│   ├── wsgi.py              # WSGI entry point for web servers.
│   └── templates/           # Global templates directory.
│       └── base.html        # Shared base HTML template with navigation layout.
├── cars/                    # Django application managing cars and brands.
│   ├── __init__.py          # Initialization file for the cars Python package.
│   ├── admin.py             # Admin interface registration for Brand and Car models.
│   ├── apps.py              # App config (imports and registers database signals).
│   ├── forms.py             # Form validation rules (minimum price, minimum year).
│   ├── models.py            # DB schema definitions (Brand, Car, CarInventory).
│   ├── signals.py           # Pre-save (AI description) and post-save/delete signals.
│   ├── tests.py             # Unit tests for checking signals and AI generation flow.
│   ├── views.py             # CRUD views using class-based generic views.
│   ├── migrations/          # Database migrations for the cars app.
│   │   ├── 0001_initial.py  # Initial migration creating the Car model.
│   │   ├── 0002_brand_alter_car_brand.py # Migration adding the Brand model.
│   │   ├── 0003_car_photo_car_plate.py # Migration adding photo and plate fields.
│   │   ├── 0004_carinventory.py # Migration adding the CarInventory model.
│   │   ├── 0005_car_description.py # Migration adding the description field.
│   │   └── __init__.py      # Initialization file for the migrations package.
│   └── templates/           # HTML templates for cars CRUD views.
│       ├── car_delete.html  # Confirmation page for deleting a car.
│       ├── car_detail.html  # Detailed information page for a specific car.
│       ├── car_update.html  # Edit form page for updating car details.
│       ├── cars.html        # List view showing all cars with search filters.
│       └── new_car.html     # Registration form page for adding a new car.
└── media/                   # User-uploaded files directory.
    └── cars/                # Directory storing uploaded car photos.
        ├── g63.jpg          # Sample car image file.
        ├── g63_ykUQxj5.jpg  # Sample car image file.
        ├── m4-competition.jpg # Sample car image file.
        └── volvo-xc60.jpg   # Sample car image file.
```