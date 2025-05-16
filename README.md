


## Installation

Start by cloning the repository, then navigate to the project directory and run the following to set up python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then create the environment variables file:

```bash
cp .env.example .env
```

And populate with the required variables. Here you will to set up Azure Open AI, Azure AI Search, Azure Speech Services, and Azure Blob Storage. Also you will need to create a couple API tokens on a VE and SP SWOOP instance.


## Usage

To run the application, use the following command:

```bash
bash run.sh
```

If you want to try the CLI speech demo, you can run:

```bash
bash run.sh speech.py
```
