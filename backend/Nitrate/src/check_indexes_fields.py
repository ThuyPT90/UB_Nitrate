import os
import ast

TCMS_DIR = "tcms"  # thư mục chính
results = []

def extract_model_fields_and_indexes(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    class_definitions = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    for cls in class_definitions:
        fields = set()
        indexes_fields = []
        meta_class = None

        # Tìm các trường trong model
        for item in cls.body:
            if isinstance(item, ast.Assign):
                if isinstance(item.targets[0], ast.Name):
                    fields.add(item.targets[0].id)

            if isinstance(item, ast.ClassDef) and item.name == "Meta":
                meta_class = item

        # Tìm indexes trong Meta
        if meta_class:
            for meta_item in meta_class.body:
                if isinstance(meta_item, ast.Assign):
                    if meta_item.targets[0].id == "indexes":
                        for elt in meta_item.value.elts:
                            for kw in elt.keywords:
                                if kw.arg == "fields":
                                    if isinstance(kw.value, ast.List):
                                        for f in kw.value.elts:
                                            if isinstance(f, ast.Str):
                                                field_name = f.s
                                                indexes_fields.append(field_name)
        
        # So sánh
        missing = [f for f in indexes_fields if f not in fields]
        if missing:
            results.append((filepath, cls.name, missing))

# Duyệt thư mục
for root, _, files in os.walk(TCMS_DIR):
    for file in files:
        if file.endswith(".py"):
            extract_model_fields_and_indexes(os.path.join(root, file))

# In kết quả
print("\n🔍 Các lỗi phát hiện:")
if results:
    for filepath, model, missing_fields in results:
        print(f"[{filepath}] ❌ Model `{model}` thiếu field: {missing_fields}")
else:
    print("✅ Không phát hiện lỗi nào!")
