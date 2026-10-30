# API de biblioteca — guia rápido e Postman

API local da questão 1: cadastro e consulta de livros. Este guia é uma segunda opção aos exemplos com `curl` do [README](../README.md).

## Iniciar a API

Com as dependências instaladas e o ambiente virtual ativado, na raiz do projeto:

```bash
python manage.py migrate
python manage.py runserver
```

Endereço padrão: `http://127.0.0.1:8000`. A API não exige autenticação, chave OpenAI ou configuração de LangSmith.

## Usar a coleção no Postman

1. Abra o Postman e escolha **Import** (ou **Use resources or import → Import**, conforme a versão).
2. Copie [postman/DOT-Biblioteca.postman_collection.json](postman/DOT-Biblioteca.postman_collection.json) para uma pasta de trabalho do Postman fora deste projeto e importe essa cópia. Assim, uma conversão feita pelo aplicativo não altera o arquivo da entrega.
3. Abra a coleção **DOT - Questão 1 - API de biblioteca**. Em **Variables**, confira `base_url = http://127.0.0.1:8000`, sem barra final. Não é preciso importar um arquivo de ambiente.
4. Envie **1 - Cadastro → Cadastrar livro - 201**.
5. Experimente as requisições das pastas **2 - Consultas** e **3 - Validações**, clicando em **Send**. Compare o status/corpo retornado com o exemplo salvo na requisição.

Cada envio do cadastro válido cria outro registro no SQLite local. Títulos repetidos são permitidos. Os exemplos salvos foram capturados executando as nove requisições com o cliente de testes do DRF e um banco SQLite isolado, inicialmente vazio; não são exemplos capturados pela interface do Postman. Os IDs e a quantidade de resultados na sua API podem ser diferentes. Esta coleção não contém scripts de teste: a suíte automatizada principal continua sendo `python manage.py test`.

Se usar outra porta, altere apenas `base_url` na coleção. Se usar o Postman no navegador, selecione o **Desktop Agent** para alcançar a API local; o aplicativo desktop também pode ser usado diretamente.

## Contrato dos endpoints

### POST `/api/livros/`

Envia um objeto JSON com `Content-Type: application/json`.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `titulo` | Texto | Obrigatório, até 255 caracteres. |
| `autor` | Texto | Obrigatório, até 255 caracteres. |
| `data_publicacao` | Data | Obrigatória, data válida em `AAAA-MM-DD`. |
| `resumo` | Texto | Obrigatório, até 10.000 caracteres. |

Valores ausentes, nulos, vazios ou apenas com espaços são recusados. `id` é gerado pelo servidor. Datas futuras e livros com títulos repetidos são aceitos.

Exemplo de corpo, também preenchido na coleção:

```json
{
  "titulo": "Python Fluente",
  "autor": "Luciano Ramalho",
  "data_publicacao": "2022-05-10",
  "resumo": "Uma introdução à programação idiomática em Python."
}
```

- **201 Created:** objeto cadastrado, com os quatro campos e `id`.
- **400 Bad Request:** objeto com mensagens por campo. Por exemplo, `{}` gera erros nos quatro campos, e `2023-02-29` gera erro em `data_publicacao`.

### GET `/api/livros/`

Retorna **200 OK** com um array de livros, ordenado por `id` crescente, sem paginação. O banco vazio ou uma consulta sem correspondências retorna `[]`.

| Parâmetros | Comportamento |
| --- | --- |
| Sem parâmetros | Lista todos os livros. |
| `titulo=PYTHON` | Título contendo o texto, sem diferenciar maiúsculas/minúsculas. |
| `autor=ramalho` | Autor contendo o texto, sem diferenciar maiúsculas/minúsculas. |
| `titulo=python&autor=ramalho` | **E**: o livro deve corresponder aos dois filtros. |
| `titulo=&autor=` | Filtros vazios são ignorados; lista todos os livros. |
| `titulo=__dot_sem_correspondencia__` | Exemplo de consulta sem resultados, desde que nenhum título contenha esse marcador. |

As pesquisas são parciais e literais. Espaços nas extremidades são removidos. A comparação de caixa cobre letras acentuadas: `álvaro` encontra `ÁLVARO`, mas `alvaro` não. Acentos continuam significativos. Parâmetros desconhecidos são ignorados; se um parâmetro for repetido, vale seu último valor.

### Outros retornos

- **400:** JSON malformado.
- **415:** tipo de conteúdo não suportado no cadastro.
- **405:** PUT, PATCH ou DELETE na coleção de livros.

Use sempre a barra final em `/api/livros/`. Não há rotas de edição, exclusão ou detalhe; a coleção cobre apenas o escopo entregue.

## Requisições incluídas

| Pasta | Requisição | Status esperado |
| --- | --- | --- |
| Cadastro | Cadastrar livro | 201 |
| Consultas | Listar livros | 200 |
| Consultas | Filtrar por título | 200 |
| Consultas | Filtrar por autor | 200 |
| Consultas | Combinar título e autor | 200 |
| Consultas | Ignorar filtros vazios | 200 |
| Consultas | Consulta sem resultados | 200, com `[]` no cenário de exemplo |
| Validações | Campos obrigatórios ausentes | 400 |
| Validações | Data impossível | 400 |

Formato da coleção: **Postman Collection v2.1**, com descrições em português e exemplos de resposta. Consulte a [documentação oficial de importação](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data) e o [schema oficial](https://schema.postman.com/json/collection/v2.1.0/docs/index.html).
