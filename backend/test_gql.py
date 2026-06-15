import requests
query = '''mutation {
  createTariff(name: "Test 2", price: 100.0, minutes: 60) {
    success
    tariff { id name price minutes hoursDisplay isActive }
  }
}'''
r = requests.post('http://127.0.0.1:8000/graphql/', json={'query': query})
print(r.status_code)
print(r.json())
