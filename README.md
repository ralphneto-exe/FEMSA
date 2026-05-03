# FEMSA
Dashboard mostrando total de vendas, projeções mensais e participação de cada classe de produtos no total.

Estrutura Técnica do Dashboard
O código transforma uma planilha de Excel em uma ferramenta interativa de análise de performance de vendas/operações. Ele foi construído em quatro pilares principais:

1. Configuração e Estilo (O "Look & Feel")
Identidade Visual: Define uma paleta de tons de vermelho para manter a consistência entre todos os gráficos (mix, evolução e precisão).

Modo Impressão: Utiliza CSS injetado para esconder botões e a barra lateral quando o usuário tenta imprimir a página, garantindo um relatório limpo em PDF.

2. Tratamento de Dados Robusto
Cache (@st.cache_data): Otimiza o carregamento, garantindo que o processamento do Excel só ocorra quando o arquivo for alterado.

Validação: Verifica se as colunas obrigatórias (S1 a S4, Período, etc.) existem, evitando erros de execução se o usuário subir um arquivo incorreto.

Tratamento de Datas: Converte o formato mm/aa para um objeto de data real, permitindo a ordenação cronológica correta nos gráficos.

3. Inteligência de Visualização
O dashboard divide a análise em dois níveis:

Visão Macro (Panorama Geral):

Gráfico de Pizza: Mostra a fatia de cada produto no volume total do último mês.

Gráfico de Linhas: Exibe a tendência histórica de volume por produto.

Visão de Precisão (KPIs):

Cards de Erro Médio: Utiliza o componente st.metric para mostrar rapidamente se a projeção está acima ou abaixo do realizado, com cores dinâmicas (vermelho para desvios).

Gráfico de Precisão Mensal (Plotly): Um gráfico complexo de dois eixos. As barras mostram o índice de assertividade (comparando o planejado vs. realizado), enquanto a linha pontilhada monitora o volume absoluto.

4. Interatividade e Detalhamento
Filtros Dinâmicos: A barra lateral permite selecionar meses específicos para comparar períodos diferentes.

Expansores (st.expander): Organiza a página de detalhes, permitindo que o usuário veja o gráfico de um mês específico ou abra os dados brutos em uma tabela para auditoria rápida.
