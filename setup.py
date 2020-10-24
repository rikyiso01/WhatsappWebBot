from setuptools import setup,find_packages

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='whatsappwebbot',
   version='0.0.3',
   description='A python telegram bot to forward whatsapp messages to telegram',
   license="GPL-3",
   long_description=long_description,
   author='Riccardo Isola',
   author_email='riky.isola@gmail.com',
   url="https://github.com/RikyIsola/WhatsappWebBot",
   packages=find_packages(),
   install_requires=['selenium', 'python-telegram-bot','PyVirtualDisplay'],
   scripts=['whatsappwebbot']
)
