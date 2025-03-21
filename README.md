# Anschreibeliste

## Installation

1.  Clone this repository and switch into the folder
    ```bash
    git clone https://github.com/anders0nmat/anschreibeliste && cd anschreibeliste
    ```
1.  Install requirements
    1.  Create and activate venv
        ```bash
        python -m venv .
        ```
        - Linux / Mac
            ```bash
            source bin/activate
            ```
        - Windows
            ```bash
            .\Scripts\Activate.ps1
            ```
    1.  Install requirements
        ```bash
        pip install -r requirements.txt
        ```
2.  Configure application
    1. Copy and rename `template-config.toml`
        ```bash
        cp template-config.toml config.toml
        ```
    2. Fill in `config.toml`
       - _Required:_ `secret-key`
       - _Required:_ Database configuration
1.  Initial setup
    1. Update/Create database
        ```bash
        python manage.py migrate
        ```
    2. Create Superuser
        ```bash
        python manage.py createsuperuser
        ```

## Running

1.  Update/Create database
    ```bash
    python manage.py migrate
    ```
1.  Start Server
    ```bash
    daphne anschreibeliste.asgi:application -b 0.0.0.0 -p 80
    ```

