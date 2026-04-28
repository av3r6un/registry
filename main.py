from backend import start
from datetime import datetime as dt
def main():
  print('Starting app at', dt.now().strftime('%H:%M'))
  start()


if __name__ == "__main__":
  main()
