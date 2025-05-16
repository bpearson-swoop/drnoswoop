


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

Also for the user name to ID, you need this code in the analytics engine.
```php
<?php

/**
 * Wrapper Class for getting the user id.
 *
 * Expected Query parameters:
 *     "Name" : string
 */

class WrapperGetUserID extends APIWrapperBase
{

    public $Name = null;


    /**
     * Global function, just ignore this check.
     */
    public function checkModeForFunction()
    {
        // No check required for this function
        return true;

    }//end checkModeForFunction()

    public function checkFunctionParameters()
    {
        // No check required for this function
        parse_str($this->QueryParams, $this->QueryString);
        return true;

    }//end checkFunctionParameters()

    public function extractQueryString()
    {
        $this->Name = ($this->QueryString["Name"] ?? null);
        if (is_string($this->Name)) {
            $this->Name = trim(urldecode($this->Name));
        }

    }//end extractQueryString()

    public function call()
    {
        if ($this->Name == null) {
            self::pushError("0007", "Invalid Name for this function");
        } else {
            $db = NetworkDatabase::db();
            $stmt = $db->prepare("SELECT id FROM n_user WHERE name=:name");
            $stmt->bindValue(':name', $this->Name, PDO::PARAM_STR);
            $stmt->execute();
            $result = $stmt->fetch(PDO::FETCH_ASSOC);
            if ($result) {
                $this->result = $result['id'];
            } else {
                self::pushError("0007", "Invalid Name for this function");
            }
        }//end if


    }//end call()


}//end class

```


## Usage

To run the application, use the following command:

```bash
bash run.sh
```

If you want to try the CLI speech demo, you can run:

```bash
bash run.sh speech.py
```
