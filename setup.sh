#!/bin/bash

sudo apt update
sudo apt install -y dislocker python3-dev python3.10-venv

# Create python venv
rm -rf venv # remove venv
python3 -m venv venv # create venv
source venv/bin/activate # activate venv
pip install --upgrade pip # upgrade pip
pip install -r requirements.txt # install requirements
deactivate # deactivate venv

# Generate run.sh
echo "#!/bin/bash" > run.sh
echo cd $(pwd) >> run.sh
echo export PYTHONPATH=$(pwd) >> run.sh
echo source venv/bin/activate >> run.sh
echo "python main.py >log.txt 2>&1" >> run.sh
echo deactivate >> run.sh
chmod +x run.sh
