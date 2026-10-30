# Teste técnico DOT — Backend com IA

Três soluções independentes em Python, seguindo as três questões da prova. A API usa Django/DRF e SQLite; o chatbot usa LangChain com a integração oficial OpenAI; a busca usa Sentence Transformers e FAISS local. Não é necessário iniciar a API para executar os outros módulos.

## Requisitos e entregáveis

| Questão | Requisito da prova | Arquivos principais |
| --- | --- | --- |
| 1 | Cadastrar e consultar livros por título/autor, SQLite e testes | `library/models.py`, `serializers.py`, `views.py`, `urls.py`, `migrations/0001_initial.py`, `tests.py` e `config/` |
| 2 | Entrada textual, conversa via LangChain/OpenAI e exemplos de Python | `chatbot/service.py`, `chatbot/__main__.py`, `tests/test_chatbot.py` e [exemplos](docs/exemplos-chatbot.md) |
| 3 | Documentos, embeddings, vector store, função de busca e demonstração | `data/documents.json`, `semantic_search/service.py`, `semantic_search/__main__.py` e `tests/test_semantic_search.py` |
| Todas | Instalação, configuração e decisões técnicas | Este README, `.env.example`, `requirements.in` e `requirements.txt` |

## Instalação reproduzível

Use **Python 3.12 de 64 bits**. São necessários rede e espaço em disco para instalar PyTorch e baixar o modelo de embeddings. Não é necessária GPU, chave OpenAI ou conta Hugging Face para a API, os testes ou a busca local.

Na raiz do projeto, PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install uv==0.13.6
.venv\Scripts\uv pip install --torch-backend cpu --require-hashes -r requirements.txt
```

Linux/macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install uv==0.13.6
.venv/bin/uv pip install --torch-backend cpu --require-hashes -r requirements.txt
```

Os comandos seguintes usam `python` com o ambiente ativado. Ative com `.venv\Scripts\Activate.ps1` no PowerShell ou `source .venv/bin/activate` no Linux/macOS. Se a política local bloquear a ativação, use diretamente `.venv\Scripts\python` nos comandos, sem alterar a política da máquina.

`requirements.txt` fixa dependências diretas/transitivas e hashes, com marcadores de plataforma. **Mantenha `--torch-backend cpu` na instalação**: os wheels de CPU do PyTorch para Windows/Linux vêm do índice oficial próprio. No macOS, o lock utiliza a distribuição correspondente da plataforma. O suporte a wheels de FAISS depende da plataforma; a execução desta entrega foi validada em Windows x64, não em todos os sistemas.

`requirements.in` declara intervalos permitidos. Para atualizar intencionalmente e gerar um novo lock, use uv 0.13.6 e depois valide novamente:

```bash
uv pip compile requirements.in --python-version 3.12 --universal --torch-backend cpu --emit-index-url --generate-hashes --output-file requirements.txt
```

Instale a partir de `requirements.txt`: o arquivo `requirements.in` sozinho resolveria versões novas.

## Configuração

Copie `.env.example` para `.env` (`Copy-Item .env.example .env` no PowerShell; `cp .env.example .env` no Linux/macOS). Apenas o chatbot carrega esse arquivo, sem sobrescrever variáveis já definidas no processo.

| Variável | Uso |
| --- | --- |
| `OPENAI_API_KEY` | Chave privada da conta OpenAI. Obrigatória apenas no chatbot. |
| `OPENAI_MODEL` | Identificador de um modelo OpenAI de conversa/texto disponível na sua conta. Obrigatório, sem valor padrão. |
| `LANGSMITH_TRACING` | `false` por padrão; somente `true` habilita rastreamento. |
| `LANGSMITH_API_KEY` | Necessária se o rastreamento estiver habilitado. |
| `LANGSMITH_PROJECT` | Projeto opcional dos traces; o exemplo usa `dot-backend-ia`. |

Configure `OPENAI_MODEL` com um identificador que sua conta permita usar na API, conferindo o [catálogo oficial](https://developers.openai.com/api/docs/models) e as permissões da própria conta. A API também oferece [listagem dos modelos disponíveis](https://developers.openai.com/api/reference/python/resources/models/methods/list); depois confira na ficha do escolhido o suporte a conversa/texto. Não há modelo padrão nem troca automática de modelo. Não são impostos parâmetros como `temperature`, cuja compatibilidade varia entre modelos. Modelos apenas de embeddings, áudio ou imagem não atendem ao chatbot.

O chatbot envia perguntas e o histórico da sessão à OpenAI e **pode gerar custos**. LangSmith é opcional: quando ativo, recebe também prompts, perguntas, respostas e metadados de execução. O projeto o desativa explicitamente por padrão, inclusive diante da configuração legada `LANGCHAIN_TRACING_V2`. Não coloque dados sensíveis nas demonstrações. Credenciais e `.env` estão fora do Git; `.env.example` contém apenas valores vazios.

## Questão 1 — API de biblioteca

```bash
python manage.py migrate
python manage.py runserver
```

A migration está incluída no código; não é preciso gerar novas migrations para avaliar. O arquivo `db.sqlite3` é criado localmente e está ignorado pelo Git. O servidor usa `http://127.0.0.1:8000`.

**Alternativa ao curl:** importe a [coleção do Postman](docs/postman/DOT-Biblioteca.postman_collection.json). O [guia rápido da API e do Postman](docs/api.md) explica a importação e os nove exemplos de cadastro, consultas e validação. A coleção já inclui `base_url`, sem necessidade de configurar credenciais.

| Método e caminho | Comportamento |
| --- | --- |
| `POST /api/livros/` | Cadastra um livro; retorna `201` e o objeto, incluindo `id`. |
| `GET /api/livros/` | Lista os livros por `id` crescente; retorna `200` e um array JSON. |
| `GET /api/livros/?titulo=python` | Busca parcial no título. |
| `GET /api/livros/?autor=ramalho` | Busca parcial no autor. |
| `GET /api/livros/?titulo=python&autor=ramalho` | Aplica os dois critérios com **E**: o livro deve atender a ambos. |

Campos obrigatórios: `titulo` e `autor` (até 255 caracteres cada), `data_publicacao` (data válida no formato `AAAA-MM-DD`) e `resumo` (até 10.000 caracteres). Valores ausentes, nulos, vazios ou apenas com espaços são recusados. `id` é gerado pelo servidor. Datas futuras e livros com títulos repetidos são aceitos. Uma data impossível, como `2023-02-29`, retorna `400` com mensagem associada a `data_publicacao`.

Os filtros ignoram diferenças de maiúsculas/minúsculas, inclusive letras acentuadas, e removem espaços apenas nas extremidades. Acentos continuam significativos: `álvaro` encontra `ÁLVARO`, mas `alvaro` não. O filtro é literal: `.` não funciona como expressão regular. Filtros vazios são ignorados; sem filtros, todos os registros são listados. Parâmetros não reconhecidos são ignorados. Sem correspondências, a resposta é `200` com `[]`. Para parâmetros repetidos, é considerado o último valor, conforme `QueryDict` do Django.

SQLite não oferece `icontains` Unicode completo. A view usa `iregex` do backend Django/SQLite, que executa o `re` do Python, com entrada escapada por `re.escape`. Isso resolve a comparação com acentos sem duplicar campos nem alterar a base. A busca faz varredura e é proporcional ao pequeno escopo do desafio.

Exemplos executáveis no PowerShell (use `curl` no Linux/macOS). O JSON em arquivo evita diferenças de escape e encoding entre shells:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/api/livros/ -H "Content-Type: application/json" --data-binary "@data/book.example.json"
curl.exe -i --get http://127.0.0.1:8000/api/livros/ --data-urlencode "titulo=PYTHON"
curl.exe -i --get http://127.0.0.1:8000/api/livros/ --data-urlencode "autor=ramalho"
curl.exe -i --get http://127.0.0.1:8000/api/livros/ --data-urlencode "titulo=python" --data-urlencode "autor=ramalho"
curl.exe -i --get http://127.0.0.1:8000/api/livros/ --data-urlencode "titulo=inexistente"
```

Formato ilustrativo de erro ao enviar `{}` (as mensagens são traduzidas pelo DRF):

```json
{
  "titulo": ["Este campo é obrigatório."],
  "autor": ["Este campo é obrigatório."],
  "data_publicacao": ["Este campo é obrigatório."],
  "resumo": ["Este campo é obrigatório."]
}
```

Use sempre a barra final da rota, especialmente no POST. JSON malformado retorna `400`; tipo de conteúdo não suportado retorna `415`. Não há autenticação, frontend, edição, exclusão ou rota de detalhe: essas funcionalidades não são necessárias à prova. PUT/PATCH/DELETE na coleção retornam `405`.

## Questão 2 — Chatbot de Python

Após configurar as duas variáveis OpenAI:

```bash
python -m chatbot
```

Pergunte `Como criar uma lista em Python?` e depois `E como adicionar um item nela?` para verificar o contexto. Digite `sair` ou `/sair` para encerrar; EOF e Ctrl+C também encerram. Linhas vazias são ignoradas. Outras perguntas e **respostas ilustrativas, não saídas capturadas do provedor**, estão em [docs/exemplos-chatbot.md](docs/exemplos-chatbot.md).

Fluxo: texto do terminal → `ChatPromptTemplate` com instrução em português e histórico → `ChatOpenAI` de `langchain-openai` → `StrOutputParser` → resposta no terminal. Essa composição LCEL usa os pacotes atuais `langchain-core` e `langchain-openai`; não precisa do metapacote `langchain`, agentes ou chains legadas.

Cada `ChatSession` mantém sua própria lista de mensagens em memória. O histórico é atualizado apenas quando uma resposta textual é recebida. Uma falha do provedor mantém a sessão utilizável sem registrar um turno incompleto. O modelo tem timeout de 30 segundos e no máximo uma retentativa automática do SDK; o tempo total pode superar 30 segundos com a retentativa.

Credenciais ausentes encerram com código 1 e instrução de configuração. Falhas de autenticação, rede/timeout, cota, acesso ao modelo e solicitações incompatíveis produzem mensagens claras sem imprimir o erro bruto do provedor. Não há fallback silencioso para outro modelo.

## Questão 3 — Busca semântica

```bash
python -m semantic_search index
python -m semantic_search search "Como tirar valores repetidos de uma coleção?" --top-k 3
python -m semantic_search search "Quero lidar com falhas sem derrubar meu programa" --top-k 3
python -m semantic_search search "Processar muitos dados sem guardar tudo na memória" --top-k 3
```

Os comandos usam `data/documents.json` e `artifacts/semantic_index/` por padrão. Para outro corpus e diretório:

```bash
python -m semantic_search index --documents data/documents.json --index-dir artifacts/outro_indice
python -m semantic_search search "Guardar uma idade para cada pessoa" --index-dir artifacts/outro_indice --top-k 2
```

Função de consulta reutilizável em Python:

```python
from semantic_search.service import SemanticSearch

searcher = SemanticSearch()  # carrega o índice e o modelo uma vez
results = searcher.search("Adicionar um elemento ao final de uma sequência", top_k=3)
for result in results:
    print(result["id"], result["score"], result["text"])
```

Cada resultado contém `id`, `text` e `score`. `top_k` precisa ser inteiro positivo e é limitado à quantidade de documentos; nunca há posições artificiais para completar resultados. A busca sempre retorna os vizinhos mais próximos: uma consulta fora do assunto também recebe resultados, sem garantir relevância absoluta.

O corpus contém oito textos curtos originais em português: listas, dicionários, conjuntos, exceções, arquivos, geradores, asyncio e funções. As consultas abaixo exemplificam a busca por significado sem exigir o nome do conceito no texto da pergunta:

| Consulta | Documento relevante esperado |
| --- | --- |
| Como tirar valores repetidos de uma coleção? | `conjuntos` |
| Quero lidar com falhas sem derrubar meu programa | `excecoes` |
| Processar muitos dados sem guardar tudo na memória | `geradores` |

Essas correspondências são exemplos para demonstração; o ranking depende dos embeddings e do corpus.

### Modelo, pré-processamento e métrica

- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, com revisão fixa em `semantic_search/service.py`. É um modelo de similaridade multilíngue, incluindo português, viável em CPU e com embeddings de 384 dimensões. É adequado como base simples para esse corpus curto; não há alegação de ser o melhor modelo para qualquer domínio.
- **Pré-processamento:** compacta espaços e quebras de linha apenas no texto enviado ao encoder. Preserva acentos, caixa, pontuação e sintaxe de código. O texto original permanece nos resultados. Cada documento já é uma unidade curta; não há chunking automático. O código verifica o limite de tokens do modelo e recusa textos que seriam truncados (a revisão escolhida tem janela de 128 tokens, incluindo tokens especiais).
- **Métrica:** embeddings `float32` são normalizados com norma L2 tanto na indexação quanto na consulta. `faiss.IndexFlatIP` calcula produto interno; para vetores unitários ele equivale ao cosseno. `score` varia de -1 a 1, e **maior é melhor**. Não é probabilidade nem percentual de acerto. O índice faz busca exata, suficiente para oito documentos.
- **Persistência:** `index.faiss` guarda os vetores; `metadata.json` guarda textos, identificadores, modelo/revisão, dimensão, métrica e checksum. A carga recusa inconsistências e pede reconstrução. Os arquivos devem ser locais e confiáveis; checksum detecta inconsistência, não autentica arquivos de terceiros.

Na primeira indexação, o Sentence Transformers baixa os pesos da Hugging Face para o cache local (centenas de MB). Depois a inferência é local, sem custo de API. A biblioteca pode consultar metadados na rede ao carregar o modelo; com o cache completo, use `HF_HUB_OFFLINE=1` para execução estritamente offline. No PowerShell: `$env:HF_HUB_OFFLINE="1"`; no Linux/macOS: `export HF_HUB_OFFLINE=1`. Não habilite isso antes do download inicial.

Um aviso de symlinks no Windows pode indicar apenas uso menos eficiente do cache; não exige executar como administrador. A indexação imprime o destino ao terminar. O índice gerado não é versionado, pois é derivado dos documentos e dos pesos fixados.

As consultas carregam os vetores persistidos e calculam **somente o embedding da consulta**. Reutilizar `SemanticSearch` mantém o modelo em memória entre consultas; novos processos CLI carregam novamente o modelo, sem recalcular embeddings dos documentos. Para reconstruir após editar documentos ou trocar modelo/pré-processamento, execute novamente `python -m semantic_search index`. Até lá, consultas usam o snapshot anterior. A carga não tenta reindexar silenciosamente.

## Testes e avaliação

Sem credenciais, download do modelo ou chamadas cobradas:

```bash
python manage.py test -v 2
```

Por módulo:

```bash
python manage.py test library -v 2
python -m unittest tests.test_chatbot -v
python -m unittest tests.test_semantic_search -v
```

Os testes da API usam `APITestCase`: banco SQLite em memória exclusivo do runner, migrations aplicadas, destruição automática e isolamento entre testes. Eles não acessam `db.sqlite3`. Os testes do chatbot mantêm prompt/parser reais e mockam o modelo; verificam contexto, isolamento de sessões e falhas. Na busca, usam FAISS real, vetores conhecidos e diretórios temporários, sem baixar o modelo. Esses vetores testam a matemática/persistência, não a qualidade linguística.

Verificações adicionais:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
uv pip check
```

A sequência sugerida para avaliação é instalar o lock, executar os testes, aplicar migrations, testar GET/POST com curl ou Postman, indexar/consultar os documentos e, por último, configurar um modelo autorizado para o chatbot.

## Referências oficiais consultadas

- [DRF — generic views e ListCreateAPIView](https://www.django-rest-framework.org/api-guide/generic-views/).
- [Django 5.2 — limitações de comparação no SQLite](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes).
- [LangChain — integração ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai).
- [Sentence Transformers — modelos multilíngues e português](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html#multilingual-models).
- [Ficha oficial do modelo de embeddings](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).
- [FAISS — produto interno e cosseno](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances).
- [uv — instalação de PyTorch e builds de CPU](https://docs.astral.sh/uv/guides/integration/pytorch/).
