sass docs/style.scss:docs/style.css

cat > docs/README.html << EOF
<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="utf-8" />
<title>README</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
EOF
marked --gfm --breaks README.md >> docs/README.html
cat >> docs/README.html << EOF
</body>
</html>
EOF
