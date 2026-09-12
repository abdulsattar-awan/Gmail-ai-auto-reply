person = {
    "name": "Ali",
    "age": 22,
    "city": "Lahore"
}
print(person["name"])
print(person["age"])
print(person["city"])
print(person.get("name"))
print(person.get("email", "Not found"))