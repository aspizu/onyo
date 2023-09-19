sass docs/style.scss:docs/style.css

cat > docs/itertools.html << EOF
<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="utf-8" />
<title>itertools.onyo</title>
<link rel="stylesheet" href="syntax.css" />
</head>
<body>
<pre><code>
EOF
onyoc --syntax-highlight -i examples/tests/itertools.onyo | cat >> docs/itertools.html
cat >> docs/itertools.html << EOF
</pre></code>
</body>
</html>
EOF
