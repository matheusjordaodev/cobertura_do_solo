import geemap
import geemap.foliumap as geemap
import ee
import geopandas as gpd 
import streamlit as st
import streamlit_folium
import pandas as pd 
import plotly.express as px
import json
import os 
from palette_biome import paleta_cores
from palette_biome import paleta_nomes
from palette_biome import dicionario_classes
from palette_biome import dicionario_cores

# Configuração da página
st.set_page_config(layout="wide")
st.title('Dashboard MapBiomas - Select Region')
st.markdown(""" #### O APP foi desenvolvido para que o usuário possa carregar a região de interesse, definir o ano e visualizar a classificação. A aplicação processa Datasets disponíveis no Google Earth Engine.
#### Para mais informações sobre o projeto do MapBiomas acesse a página disponível em [https://brasil.mapbiomas.org/](https://brasil.mapbiomas.org/).
#### Caso você não possua uma base de dados no formato **GeoJSON** crie o arquivo utilizando o site [geojson.io](https://geojson.io/#new&map=2/0/20).""")

st.divider()

# Carrega a imagem da logo
logo_image = 'bluebell_logo.png'
# Exibe a imagem no sidebar
st.sidebar.image(logo_image, width=200)

st.sidebar.markdown("""
    ## Como usar o Dashboard MapBiomas
    Este aplicativo foi desenvolvido para facilitar a visualização e análise de dados de classificação do MapBiomas. Siga estas etapas simples para utilizá-lo:
    1. **Seleção da Região de Interesse:** Carregue um arquivo GeoJSON definindo a região de interesse ou utilize a ferramenta de desenho no mapa.
    2. **Seleção do Ano:** Escolha o ano de interesse na barra lateral para visualizar a classificação correspondente.
    3. **Visualização da Classificação:** O mapa principal exibirá a classificação do MapBiomas para a região e o ano selecionados.
    4. **Análise dos Dados:** Abaixo do mapa, você encontrará um gráfico de área mostrando a distribuição da área por classe ao longo dos anos, bem como uma tabela com os detalhes da área de cada classe.
    5. **Gráfico de Área (%):** Na aba ao lado, você encontrará um gráfico de pizza mostrando a distribuição percentual da área para as classes no último ano disponível.
    6. **Exploração Adicional:** Explore as opções disponíveis no sidebar e aproveite a experiência!
    ---
""")



##Autenticação
# @st.cache_data
# def m():
m=geemap.Map(heigth=800)
m.setOptions("HYBRID")
# return m

# # ##Armazendo dado em cache 
# m=m()

##Seleção da imagem
@st.cache_data
def mapbiomas():
    #image = ee.Image('projects/mapbiomas-workspace/public/collection8/mapbiomas_collection80_integration_v1')
    image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')
    
    
    return image

##Bandas
lista = list(mapbiomas().bandNames().getInfo())
lista_img=[]

##Lista de imagens
for i in range(len(lista)):
    band_name = lista[i]
    img = mapbiomas().select(str(band_name))
    lista_img.append(img)

years = ee.List.sequence(1985,2022,1)
collection =ee.ImageCollection.fromImages(lista_img)

# Definir uma função para adicionar o ano como uma propriedade a cada imagem
def add_year(image):
    # Obter o nome da primeira banda da imagem
    first_band_name = ee.String(ee.Image(image).bandNames().get(0))
    # Extrair os últimos quatro caracteres do nome da banda para obter o ano
    year = first_band_name.slice(-4)
    # Adicionar a propriedade 'year' à imagem
    return image.set('year', year).set('band', first_band_name)

# Aplicar a função a cada imagem na coleção usando map()
collection_with_year = collection.map(add_year)


##Dataframe 
@st.cache_data
def df_col():
    data_table = pd.DataFrame({
            "Ano": collection_with_year.aggregate_array("year").getInfo(),
            "Banda": collection_with_year.aggregate_array("band").getInfo(),
        })
    return data_table

df_col=df_col()

# Criar lista de botões para cada data
st.subheader('Clique no botão para selecionar o ano')
selected_dates = st.multiselect("Selecione o ano", df_col["Ano"].tolist())

##Criar um ambiente onde a partir de um botão selecione a image pelo filtro
# Filtrar a coleção com base nas datas selecionadas
selected_collection = collection_with_year.filter(ee.Filter.inList('year', selected_dates))
listOfImages = collection_with_year.toList(collection_with_year.size())

palette_list = list(paleta_cores.values())
# m.addLayer(selected_collection, {'palette':palette_list,
#            'min':0,'max':62},str(f'Mapa de uso {selected_dates}'))
# m.centerObject(selected_collection,10)
# m.to_streamlit()


# Adicione um widget de upload de arquivo no sidebar para permitir ao usuário carregar o GeoJSON
st.subheader('Após selecionar o período de interesse, faça o upload de seu GeoJson.')
uploaded_file = st.file_uploader("Carregar GeoJSON", type=["geojson"])


def clip(image):
    return image.clip(roi).copyProperties(image, image.propertyNames())

if uploaded_file is not None:
    ##Carregando o arquivo json
    f_json = json.load(uploaded_file)
    ##selecionando as features
    f_json = f_json['features']
    # Converte de GeoDataFrame para JSON
    # Necessário para autenticação do código via GEE
    st.sidebar.write("Arquivo GeoJSON carregado com sucesso!")
    # Carrega a FeatureCollection no Earth Engine
    roi = ee.FeatureCollection(f_json)
    # Adicione a área de estudo ao mapa
    m.addLayer(roi, {}, 'Área de Estudo')
    # Recorta a coleção com base na área de interesse (ROI)
    selected_collection = selected_collection.map(clip)
    # Centralize o mapa na área de estudo
    m.centerObject(roi)
else:
    selected_collection = collection_with_year
 

# Adiciona a ROI se ela existir
if selected_dates:
    filtered_collection = selected_collection.filter(ee.Filter.inList('year', selected_dates))
    # Adicionar a camada filtrada ao mapa
    for year in selected_dates:
        filtered_collection_year = filtered_collection.filter(ee.Filter.eq('year', year))
        m.addLayer(filtered_collection_year, {'palette': palette_list, 'min': 0, 'max': 62}, f'Mapas de uso {year}')
        # Define the output directory for downloaded data
   
   # Função para exportar a imagem para um arquivo GeoTIFF
    def export_image(image, name):
        try:
            # Exporta a imagem diretamente para o ambiente de deploy
            url = image.getDownloadURL({'name':f'classification_{year}','scale': 30, 'crs': 'EPSG:4674', 'region': roi.geometry().getInfo()})
            st.success(f"Imagem exportada de {year} com sucesso. Baixe [aqui]({url}).")
        except Exception as e:
            st.error(f"Erro ao exportar a imagem: {str(e)}")
    # Botão para acionar o download dos dados
    if st.button("Download dos Dados"):
        # Verifica se a ROI está definida
        if 'roi' in locals() and roi is not None:
            # Exporta a coleção selecionada para arquivos GeoTIFF
            for year in selected_dates:
                # Filtra a coleção para o ano selecionado
                selected_collection_year = selected_collection.filter(ee.Filter.eq('year', year))
                # Exporta a primeira imagem na coleção filtrada
                name = f'image_{year}.tif'
                export_image(selected_collection_year.first(), name)
        else:
            st.warning("Por favor, selecione uma área de interesse antes de fazer o download.")

    # # Função para exportar a imagem para um arquivo GeoTIFF
    # def export_image(image, filename):
    #     try:
    #         geemap.ee_export_image(image, filename, scale=30, crs='EPSG:4674')
    #         st.success(f"Imagem exportada com sucesso: {filename}")
    #     except Exception as e:
    #         st.error(f"Erro ao exportar a imagem: {str(e)}")

    # # Button to trigger data download
    # if st.button("Download Data"):
    #     out_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    #     filename = os.path.join(out_dir, 'image.tif')
    #     export_image(selected_collection.first(), filename)
     



else:
    filtered_collection = selected_collection.filter(ee.Filter.eq('year', '2022')) 
    m.addLayer(filtered_collection, {'palette': palette_list, 'min': 0, 'max': 62}, f'Mapas de uso 2022')

if uploaded_file:
    # Filtrar a coleção com base nos anos selecionados
    selected_collection = selected_collection.filter(ee.Filter.inList('year', selected_dates))

        # Adicionar camadas aos mapas existentes
    for year in uploaded_file:
        filtered_collection_year = selected_collection.filter(ee.Filter.eq('year', year))
        m.addLayer(filtered_collection_year, {'palette': palette_list, 'min': 0, 'max': 62}, f'Mapas de uso {year}')
         # Adicionar a camada filtrada ao mapa
        # m.addLayer(selected_collection, {'palette': palette_list, 'min': 0, 'max': 62}, f'Mapas de uso {selected_dates}')
        m.centerObject(roi, 12)
else:
    m.centerObject(filtered_collection, 6)
            
# Renderizar o mapa no Streamlit
m.to_streamlit()
st.divider()
# Verifica se um arquivo foi carregado
if uploaded_file:
    # DataFrame para armazenar os resultados
    df = []

    # Itera sobre cada imagem na coleção
    for i in range(len(selected_dates)):
        # Obtém a imagem da coleção
        image = ee.Image(filtered_collection.toList(filtered_collection.size()).get(i)).clip(roi)

        # Obtém o ano da imagem
        year = int(selected_dates[i])

        # Calcula a área dos pixels de classificação
        areaImage = ee.Image.pixelArea().divide(1e4).addBands(image)

        # Reduz as áreas por classificação
        areas = areaImage.reduceRegion(
            reducer=ee.Reducer.sum().group(**{
                'groupField': 1,
                'groupName': 'classification' + '_' + str(year),
            }),
            geometry=roi,
            scale=30,
            bestEffort=True,
            maxPixels=1e13
        )

        # Converte o resultado em DataFrame
        area_df = pd.DataFrame(areas.get('groups').getInfo(), columns=['classification' + '_' + str(year), 'sum'])

        # Adiciona colunas extras
        area_df['ano'] = year
        area_df['area'] = area_df['sum'].round(2)
        area_df['classe'] = area_df['classification' + '_' + str(year)]
        area_df['nome_classe'] = area_df['classe'].replace(dicionario_classes)

        # Remove colunas desnecessárias
        area_df = area_df.drop(columns=['classification' + '_' + str(year), 'sum'], axis=1)

        # Adiciona ao DataFrame principal
        df.append(area_df)

    # DataFrame completo
    df_completo = pd.concat(df, axis='index').round(2)

    # Criando coluna de classe e de área
    df_melt = pd.melt(df_completo, id_vars=['ano', 'classe', 'nome_classe'], value_vars='area', value_name="Area_ha", var_name='Área_classe').dropna()

    # Exibe o DataFrame com a opção de seleção de anos
    
    # Calcula a área total por classe e por ano
    area_total_por_classe = df_melt.groupby(['ano', 'nome_classe'])['Area_ha'].sum().reset_index()

    # Cria o gráfico de barras
    # Cria o gráfico de área
    fig = px.area(df_melt, 
                    x='ano', 
                    y='Area_ha', 
                    color='nome_classe',
                    color_discrete_map=paleta_nomes,
                    title="Área por Classe por Ano",
                    labels={'ano': 'Ano', 'Area_ha': 'Área (ha)'})

    # Atualiza o layout do gráfico
    fig.update_layout(xaxis_tickangle=-45)

    col1, col2 = st.columns([0.5,0.5])

    with col1:
         
        tab1, tab2 = st.tabs(["📈 Chart", "🗃 Data"])

        tab1.subheader("Gráfico de Área")
        tab1.plotly_chart(fig)

        tab2.subheader("Planilha de Área")
        tab2.table(df_melt)

    # Seleciona apenas os dados para o último ano disponível
    # Agrupa os dados por ano e classe e calcula a área total
    area_total_por_ano_classe = df_melt.groupby(['ano', 'nome_classe'])['Area_ha'].sum().reset_index()
    ultimo_ano = area_total_por_ano_classe['ano'].max()
    dados_ultimo_ano = area_total_por_ano_classe[area_total_por_ano_classe['ano'] == ultimo_ano]

    # Cria o gráfico de pizza
    fig_pizza = px.pie(dados_ultimo_ano, 
                    values='Area_ha', 
                    names='nome_classe', 
                    title=f'Área por Classe no Ano {ultimo_ano}',
                    color='nome_classe',
                    color_discrete_map=paleta_nomes)

    with col2:
        st.subheader("Gráfico de Área (%)")
        st.plotly_chart(fig_pizza)


st.sidebar.markdown('Desenvolvido por [Christhian Cunha](https://www.linkedin.com/in/christhian-santana-cunha/)')