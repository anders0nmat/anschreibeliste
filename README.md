# Anschreibeliste

## Installation

1.  Clone this repository and switch into the folder
    ```bash
    git clone https://github.com/anders0nmat/anschreibeliste && cd anschreibeliste
    ```
1.  Install requirements
    1.  Create and activate venv
        ```bash
        python -m venv .venv
        ```
        - Linux / Mac
            ```bash
            source .venv/bin/activate
            ```
        - Windows
            ```bash
            .venv\Scripts\Activate.ps1
            ```
    1.  Install requirements
        ```bash
        pip install -r requirements.txt
        ```
2.  Configure application
    1. Go through `anschreibeliste/settings.py` and fill the settings as needed
        - Make sure `DEBUG` is set to `False`
        - Other things you might want to configure:
          - Database
          - Timezone
          - Language
          - App-specific settings (e.g. transaction timeout)
    2. Configure your secrets in the `secrets.toml` file
       1. Rename the `secrets-template.toml` to `secrets.toml`
       2. Configure as necessary
3.  Initial setup
    1. Update/Create database
        ```bash
        python manage.py migrate
        ```
    2. Create Superuser
        ```bash
        python manage.py createsuperuser
        ```
    3. Collect Staticfiles
        ```bash
        python manage.py collectstatic
        ```

## Running

1.  Start Server
    ```bash
    daphne anschreibeliste.asgi:application -b 0.0.0.0 -p 80
    ```
    
## Updating

1. Make sure your server is not running
2. Pull latest sources
   ```bash
   git pull
   ```
3. Migrate database
   ```bash
   python manage.py migrate
   ```
4. Collect static files
   ```bash
   python manage.py collectstatic
   ```
