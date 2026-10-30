# Exemplos didáticos do chatbot

As respostas abaixo são **ilustrativas, escritas para documentar o comportamento esperado**. Não foram obtidas por uma chamada real à OpenAI. O modelo configurado pode responder de outra forma.

## Listas e continuidade da sessão

**Pergunta:** Como criar uma lista em Python?

**Resposta ilustrativa:** Uma lista reúne vários valores em uma sequência ordenada. Em Python, você pode usar colchetes:

```python
frutas = ["maçã", "banana", "uva"]
print(frutas[0])  # maçã
```

Os índices começam em zero. Por isso, `frutas[0]` acessa o primeiro elemento. Uma lista é mutável: você pode alterar os seus itens ou acrescentar outros. Ela também pode começar vazia:

```python
compras = []
compras.append("arroz")
print(compras)  # ['arroz']
```

`append` acrescenta um elemento ao final da própria lista; seu retorno é `None`, portanto não use `compras = compras.append(...)`.

**Pergunta seguinte, na mesma sessão:** E como adicionar um item nela?

**Resposta ilustrativa:** Na lista `frutas` do exemplo anterior, use `frutas.append("laranja")`. O elemento será acrescentado ao final, preservando os anteriores. Para acrescentar vários elementos de outra sequência, use `extend`.

## Dicionários

**Pergunta:** Qual é a diferença entre uma lista e um dicionário?

**Resposta ilustrativa:** Uma lista acessa valores pela posição, como `frutas[0]`. Um dicionário associa chaves a valores, como `idades = {"Ana": 30}`; `idades["Ana"]` retorna `30`. Prefira uma lista para uma sequência de elementos e um dicionário para localizar valores por uma chave.

## Tratamento de erros

**Pergunta:** Como tratar um texto que não pode ser convertido em número?

**Resposta ilustrativa:** Capture `ValueError`, a exceção esperada ao converter um texto inadequado com `int`:

```python
try:
    quantidade = int("abc")
except ValueError:
    print("Informe um número inteiro.")
```

Esse exemplo imprime a mensagem do `except`. Capture erros específicos para não esconder falhas de programação sem relação com a conversão.

Para experimentar, execute `python -m chatbot` com credenciais/modelo configurados. Digite `sair` para encerrar. Os testes usam mocks e não afirmam validar a qualidade da resposta de um modelo real.
