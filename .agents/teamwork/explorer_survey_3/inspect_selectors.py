import re

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    q_all = set(re.findall(r'querySelector(?:All)?\([\'"]([^\'"]+)[\'"]\)', content))
    get_id = set(re.findall(r'getElementById\([\'"]([^\'"]+)[\'"]\)', content))
    data_attrs = set(re.findall(r'data-[\w-]+', content))
    events = set(re.findall(r'addEventListener\([\'"]([^\'"]+)[\'"]', content))
    
    print(f"=== {filepath} ===")
    print(f"getElementById ({len(get_id)}):")
    for s in sorted(get_id):
        print(f"  #{s}")
    print(f"\nquerySelector ({len(q_all)}):")
    for s in sorted(q_all):
        print(f"  {s}")
    print(f"\nUnique data attributes ({len(data_attrs)}):")
    for d in sorted(data_attrs):
        print(f"  {d}")

analyze_file('static/thumbnail_studio.js')
