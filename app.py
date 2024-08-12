#Inicio de APP
import json
from flask import Flask, flash, redirect, render_template, request, jsonify, send_file, session, url_for
from flask_bcrypt import Bcrypt
import pandas as pd
import pyodbc


try:
  print("Sucesso na Ligação ")
except Exception as e:
  print("Falha de ligacao new APP")

app = Flask(__name__)
app.secret_key = 'secretkeysparepartscroston'


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
  return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)