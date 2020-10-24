python setup.py sdist bdist_wheel
xclip -selection clipboard -i < pypi.txt
python -m twine upload dist/*
rm -rf build
rm -rf dist
rm -rf whatsappwebbot.egg-info