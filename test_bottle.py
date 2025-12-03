from UmiOCR_data.py_src.server.bottle import Bottle, run

app = Bottle()

@app.route('/')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    run(app, host='localhost', port=8080, debug=True)