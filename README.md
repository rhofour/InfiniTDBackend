# InfiniTD Backend

This is the backend for InfiniTD: an incremental, multiplayer tower defense game. The hosted version is available at https://infinitd.rofer.me/. The frontend can be found at https://github.com/rhofour/InfiniTDFrontend.

The code is written primarily in Python with C++ used for the battle calculation.

## Development server

To start up the development server run:

```pipenv run python -m infinitd_server --debug```

This will automatically reload when source files are changed.

## Production docs
There is some documentation about the production setup available in [production/PROD_SETUP.md](production/PROD_SETUP.md).

## License
The InfiniTD Backend is distributed under the [MIT license](https://choosealicense.com/licenses/mit).
