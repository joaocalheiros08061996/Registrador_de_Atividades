# main.py
import sys
import src.functions as fn

def main(args) -> None:
    fn.adicionar_caminhos_kv()
    fn.carregar_env()
    fn.carregar_arquivos_kv()
    fn.ActivityTrackerApp().run()
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv[1:])




