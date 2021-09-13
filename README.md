<br/>
<p align="center">
  <a href="https://github.com/RikyIsola/WhatsappWebBot">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Whatsapp to Telegram</h3>

  <p align="center">
    A Telegram bot to forward Whatsapp messages to Telegram
    <br/>
    <br/>
    <a href="https://github.com/RikyIsola/WhatsappWebBot/issues">Report Bug</a>
    .
    <a href="https://github.com/RikyIsola/WhatsappWebBot/issues">Request Feature</a>
  </p>
</p>

![Downloads](https://img.shields.io/github/downloads/RikyIsola/WhatsappWebBot/total) ![Contributors](https://img.shields.io/github/contributors/RikyIsola/WhatsappWebBot?color=dark-green) ![Stargazers](https://img.shields.io/github/stars/RikyIsola/WhatsappWebBot?style=social) ![Issues](https://img.shields.io/github/issues/RikyIsola/WhatsappWebBot) ![License](https://img.shields.io/github/license/RikyIsola/WhatsappWebBot)

## Table Of Contents

* [About the Project](#about-the-project)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Built With](#built-with)

## About The Project

Do you think Telegram is way better than Whatsapp but you have some friends that still use Whatsapp?

If so, with WhatsappWebBot it is possible to forward all Whatsapp messages to Telegram by using the web functionality

## Getting Started

Instructions to get the bot

### Prerequisites

You need to install [Docker](https://www.docker.com/)

### Installation

1. Get a Telegram API Key by asking the [BotFather](https://telegram.dog/BotFather)

2. Set the bot commands by sending to the bot father /setcommands followed by a message containing the content of the file [commands.txt](https://raw.githubusercontent.com/RikyIsola/WhatsappWebBot/main/commands.txt)

3. Create a folder where your data will be stored and in it create a file called token.txt

## Usage

Run the bot with
```bash
docker run -v "Your data folder":"/data" whatsappwebbot
```

You can now interact with it on Telegram

## Roadmap

See the [Roadmap](https://github.com/RikyIsola/WhatsappWebBot/projects) for a list of proposed features

## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.
* If you have suggestions for adding or removing projects, feel free to [open an issue](https://github.com/RikyIsola/WhatsappWebBot/issues/new) to discuss it, or directly create a pull request.
* Please make sure you check your spelling and grammar.
* Create individual PR for each suggestion.
* Please also read through the [Code Of Conduct](https://github.com/RikyIsola/WhatsappWebBot/blob/main/CODE_OF_CONDUCT.md) before posting your first idea as well.

## License

Distributed under the GPL-3 License. See [LICENSE](https://github.com/RikyIsola/WhatsappWebBot/blob/main/LICENSE) for more information.

## Built With

* [python](https://www.python.org/)
* [aiogram](https://github.com/aiogram/aiogram)
* [arsenic](https://github.com/HDE/arsenic)
* [pyyaml](https://pyyaml.org/)
* [pyvirtualdisplay](https://github.com/ponty/pyvirtualdisplay)
