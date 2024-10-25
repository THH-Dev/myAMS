import logging
from rich.console import Console
from rich.logging import RichHandler

# https://djangoandy.com/2022/07/31/how-to-add-line-numbers-and-filename-when-printing-in-python/
logging.basicConfig(
    format='%(message)s', level=logging.NOTSET, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("rich")


# https://refactoring.guru/design-patterns/singleton/python/example
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


    # https://djangoandy.com/2022/07/31/how-to-add-line-numbers-and-filename-when-printing-in-python/
# class MyLogging(metaclass=SingletonMeta):
#     def __init__(self):
#         # Configure logging to include the filename and line number
#         self.console = Console()

#     def log_message(self,str):
#         self.console.log(str, style='green')


#     def log_error(self,str):
#         self.console.log(str, style='red')

#     def log_warning(self,str):
#         self.console.log(str, style='bright_yellow')

