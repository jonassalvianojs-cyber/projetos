class Carnivore:
    def __init__(self, name):
        self.name = name

    def eat(self, prey):
        print(f"{self.name} está comendo {prey}.")

# Exemplo de uso:
leao = Carnivore("Leão")
leao.eat("zebra")