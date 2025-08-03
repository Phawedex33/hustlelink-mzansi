* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Segoe UI', sans-serif;
}

body {
  line-height: 1.6;
  background: #f7f7f7;
  color: #222;
}

.container {
  max-width: 960px;
  margin: auto;
  padding: 20px;
}

header {
  background: black;
  color: white;
  padding: 20px 0;
}

header h1 {
  text-align: center;
}

nav ul {
  list-style: none;
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

nav ul li {
  margin: 0 10px;
}

nav a {
  color: white;
  text-decoration: none;
}

.hero {
  background: #ffe600;
  padding: 60px 20px;
  text-align: center;
}

.hero h2 {
  font-size: 2rem;
  margin-bottom: 10px;
}

.btn {
  display: inline-block;
  margin-top: 15px;
  background: black;
  color: white;
  padding: 10px 20px;
  text-decoration: none;
}

.section {
  padding: 40px 20px;
  background: white;
  margin-bottom: 10px;
}

.services {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  list-style: none;
}

.services li {
  background: #eee;
  padding: 10px;
  flex: 1 1 30%;
  border-radius: 8px;
}

form input,
form textarea {
  display: block;
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

form button {
  padding: 10px 20px;
  background: black;
  color: white;
  border: none;
  cursor: pointer;
}

footer {
  text-align: center;
  padding: 20px;
  background: #333;
  color: white;
}
