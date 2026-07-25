"""Base das transgressões disciplinares do CEDM (Lei Estadual 14.310/2002).

Contém o texto literal dos 46 incisos que descrevem as transgressões
disciplinares - art. 13 (natureza grave), art. 14 (natureza média) e art. 15
(natureza leve) - acompanhados da interpretação oficial de cada um.

Fonte: Instrução Conjunta de Corregedorias nº 01, de 03/02/2014 (ICCPM/BM nº
01/14), Capítulo I, arts. 5º a 7º, que transcreve cada inciso e explica seu
alcance. O texto foi extraído dessa instrução e gravado aqui como dado offline
para que a sugestão de tipificação nunca dependa de a IA "lembrar" o artigo -
ela escolhe dentro deste conjunto fechado e o encarregado confere o texto
literal antes de aceitar.

A natureza da transgressão não define, por si só, o processo cabível: uma
transgressão de natureza grave continua sendo apurada em PCD, salvo quando
incidirem as hipóteses de PAD/PADS (art. 64 ou art. 34 do CEDM - militar no
conceito "C", ou fato que afete a honra pessoal, o pundonor militar ou o
decoro da classe). Essa decisão é da autoridade instauradora, não do sistema.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

NATUREZA_POR_ARTIGO = {13: "grave", 14: "média", 15: "leve"}


@dataclass(frozen=True)
class Transgressao:
    artigo: int
    inciso: str
    natureza: str
    texto: str
    comentario: str

    @property
    def tipificacao(self) -> str:
        """Citação seca do dispositivo, para títulos e listas na interface."""
        return f"art. {self.artigo}, inciso {self.inciso}, do CEDM (Lei 14.310/2002)"

    @property
    def texto_para_documento(self) -> str:
        """Texto que vai para o campo `tipificacao_cedm` e, dali, para o
        Despacho de Instauração e o Relatório do Encarregado.

        Traz o dispositivo, a natureza da transgressão e a conduta com as
        palavras da própria lei - é o que fundamenta a tipificação. Sai sem
        ponto final de propósito: nos modelos ele entra depois de dois-pontos
        ("Transgressão disciplinar, em tese, cometida: ___") e como aposto
        depois de vírgula ("..., Cb PM NOME, ___;"), e um deles já imprime o
        ponto em seguida. Por isso também não repete "transgressão
        disciplinar": as duas frases-modelo já trazem o termo antes do campo.
        """
        return (
            f"art. {self.artigo}, inciso {self.inciso}, do CEDM (Lei 14.310/2002), "
            f"de natureza {self.natureza}, que tipifica a conduta de “{self.texto}”"
        )

    @property
    def rotulo(self) -> str:
        return f"art. {self.artigo}, {self.inciso} ({self.natureza})"


TRANSGRESSOES: list[Transgressao] = [
    Transgressao(
        artigo=13,
        inciso="I",
        natureza="grave",
        texto=(
            "praticar ato atentatório à dignidade da pessoa ou que ofenda os princípios da cidadania e "
            "dos direitos humanos, devidamente comprovado em procedimento apuratório"
        ),
        comentario=(
            "O ato atentatório há de ser em desfavor da dignidade de pessoa determinada ou de forma que "
            "venha a ofender os princípios de direitos humanos ou da cidadania, previstos na Constituição "
            "da República de 1988, em especial nos artigos 1º e 5º, em Tratados e Convenções dos quais o "
            "Brasil é signatário, bem como em legislação infraconstitucional. A Diretriz para Produção de "
            "Serviços de Segurança Pública (DPSSP) n. 3.01.05/2010-CG, que regula a atuação da PMMG "
            "segundo a filosofia dos Direitos Humanos, estabeleceu o seguinte conceito como padrão na "
            "Educação Policial Militar: Direitos Humanos são todos os direitos que possuímos, pelo "
            "simples fato de sermos seres humanos, que nos permitem viver com dignidade, assegurando, "
            "assim, os nossos direitos fundamentais à vida, à "
            "igualdade, à segurança, à liberdade e à propriedade, dentre outros. Eles se positivam "
            "através das normas jurídicas nacionais e internacionais, tais como tratados, convenções, "
            "acordos ou pactos internacionais, leis e constituições. Estes direitos são universais, "
            "interdependentes e indivisíveis. A ofensa à dignidade deve atingir a honra, o respeito, a "
            "moral ou o decoro da pessoa. Para se configurar a mencionada transgressão, deve haver a "
            "comprovação desta em qualquer processo disciplinar, desde que este observe os primados "
            "constitucionais do devido processo legal, da ampla defesa e do contraditório. O processo "
            "disciplinar destinado à comprovação da falta poderá originar-se, contudo, de procedimentos "
            "investigativos de natureza inquisitorial comum ou militar. A conduta pode também configurar "
            "crimes militares previstos nos artigos 209 (lesão corporal), 222 (constrangimento ilegal), "
            "333 (violência arbitrária) do CPM e/ou comuns, a exemplo de abuso de autoridade e tortura. "
            "Além dos crimes, pode também constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="II",
        natureza="grave",
        texto=(
            "concorrer para o desprestígio da respectiva IME, por meio da prática de crime doloso "
            "devidamente comprovado em procedimento apuratório, que, por sua natureza, amplitude e "
            "repercussão, afete gravemente a credibilidade e a imagem dos militares"
        ),
        comentario=(
            "É imprescindível a existência de condenação com trânsito em julgado da sentença condenatória "
            "do acusado, por crime doloso, para a configuração dessa transgressão. Destarte, a conduta do "
            "militar que constitua crime, comum ou militar, e esteja ainda pendente de sentença penal "
            "condenatória transitada em julgado, para que constitua transgressão disciplinar, deverá se "
            "amoldar a outro tipo transgressivo constante dos artigos 13, 14 ou 15 do CEDM. A aplicação "
            "do referido inciso deve ser evitada, a fim de se afastar futuros questionamentos "
            "administrativos ou judiciais."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="III",
        natureza="grave",
        texto=(
            "faltar, publicamente, com o decoro pessoal, dando causa a grave escândalo que comprometa a "
            "honra pessoal e o decoro da classe"
        ),
        comentario=(
            "Para a configuração dessa transgressão, não há necessidade de que o fato ocorra em local "
            "público, uma vez que a publicidade exigida para que se configure a falta diz respeito ao "
            "comprometimento do decoro pessoal, aqui entendido como um sentimento de decência particular. "
            "O grave escândalo deve ser compreendido como algo marcantemente negativo, um fato "
            "repreensível, uma situação vergonhosa, perniciosa, cometida pelo transgressor. É necessário "
            "que tal conduta saia da normalidade e que tenha repercussão, mesmo que restrita apenas ao "
            "público interno, não carecendo de divulgação pela mídia. Há ainda, para se configurar a "
            "presente transgressão, a precípua necessidade do comprometimento da honra pessoal e do "
            "decoro da classe. A honra pessoal é o sentimento de dignidade própria, com o apreço e o "
            "respeito de que é objeto ou se torna merecedor o indivíduo, perante os concidadãos. A "
            "proposta dessa expressão é que o sentimento e o respeito afetados por aquela transgressão "
            "devem se manifestar em relação aos militares e/ou civis que presenciaram, ou de qualquer "
            "modo, tomaram ciência do fato considerado como desabonador. Decoro da classe é a repercussão "
            "do valor dos indivíduos e classes profissionais, não se tratando do valor da organização "
            "apenas, mas também da classe de indivíduos que a compõem. Ausente uma ou mais elementares na "
            "conduta adotada, a transgressão disciplinar em epígrafe não poderá ser aplicada, haja vista "
            "o fato ser considerado atípico em relação ao art. 13, inciso III, do CEDM, podendo, "
            "entretanto, se amoldar a um outro tipo transgressivo, conforme o caso. Nos termos dos "
            "artigos 34, II, e 64, II, do CEDM, independentemente do conceito em que estiver classificado "
            "o militar, a conduta por este adotada, que afetar a honra pessoal ou o decoro da classe, "
            "constitui motivo para sua submissão a PAD ou PADS. Embora o teor dos incisos em destaque em "
            "muito se assemelha à previsão do art. 13, III, do CEDM, ressalta-se que nem todo militar que "
            "se enquadrar nesse último será submetido a PAD/PADS."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="IV",
        natureza="grave",
        texto="exercer coação ou assediar pessoas com as quais mantenha relações funcionais",
        comentario=(
            "A coação constitui uma forma de constrangimento e de violência, podendo ser praticada física "
            "(material) ou moralmente, pelo superior ou subordinado. O assédio (sexual ou moral) "
            "caracteriza-se pelo constrangimento, por meio de ameaças, insinuações, propostas e até mesmo "
            "de insistentes questionamentos praticados por militares (superiores, pares ou mesmo "
            "subordinados) entre si, ou por militares em desfavor de servidores civis com quem mantenham "
            "relação funcional. Relações funcionais não significam necessariamente trabalhar na mesma "
            "Seção ou Unidade, mas se caracterizam em razão da atividade profissional, ainda que "
            "eventual. A conduta pode também configurar crimes, tanto na esfera militar - contra a "
            "Autoridade ou Disciplina Militar, contra a Administração Militar, contra a honra – quanto na "
            "esfera comum, como o próprio assédio sexual. Além dos crimes, pode também constituir "
            "transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="V",
        natureza="grave",
        texto="ofender ou dispensar tratamento desrespeitoso, vexatório ou humilhante a qualquer pessoa",
        comentario=(
            "As condutas vedadas, aduzidas no tipo, atentam contra a honra de qualquer pessoa, "
            "independente da existência de vínculo funcional entre os envolvidos. Considerando o caso "
            "concreto e a possibilidade aparente de conflito desse tipo com o art. 13, inciso I, do CEDM, "
            "prevalecerá o mais específico, não podendo os dois coexistirem num mesmo fato transgressivo. "
            "A conduta pode também configurar crime militar contra a pessoa, bem como crime comum de "
            "abuso de autoridade - e até de tortura - ou constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="VI",
        natureza="grave",
        texto=(
            "apresentar-se com sinais de embriaguez alcoólica ou sob efeito de outra substância "
            "entorpecente, estando em serviço, fardado, ou em situação que cause escândalo ou que ponha "
            "em perigo a segurança própria ou alheia"
        ),
        comentario=(
            "Para a configuração do tipo acima, deve o militar encontrar-se em qualquer uma das seguintes "
            "hipóteses, as quais podem ou não ser concomitantes: 1) em serviço; 2) fardado, mesmo que de "
            "folga; 3) qualquer situação (mesmo que de folga e em trajes civis) que cause escândalo, não "
            "necessitando de grande repercussão; 4) qualquer situação que coloque em perigo o "
            "transgressor ou outra pessoa (militar ou civil). Para o cometimento dessa transgressão, "
            "basta que o militar apresente qualquer sinal de embriaguez (como, por exemplo, voz enrolada, "
            "hálito etílico, andar cambaleante, alteração de humor etc.). A conduta poderá, também, "
            "configurar o crime militar previsto no art. 202 do CPM (embriaguez em serviço) ou constituir "
            "transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="VII",
        natureza="grave",
        texto="praticar ato violento, em situação que não caracterize infração penal",
        comentario=(
            "Em que pese ser de difícil caracterização, uma vez que quase todos os atos violentos, por si "
            "só, configuram ilícitos penais (a exemplo do constrangimento ilegal, lesão corporal, vias de "
            "fato, crimes contra a honra, homicídio, dano, insubordinação, entre outros), a transgressão "
            "em análise abarca as situações em que o militar manifesta, de forma violenta, seus gestos e "
            "opiniões, sem, contudo, cometer um crime ou contravenção penal. Como exemplos, citam-se: um "
            "murro sobre a mesa; golpes contra viaturas e outros tipos de equipamentos; xingamento "
            "indiscriminado em alto tom, dentre outros. Noutra interpretação, pode-se caracterizar tal "
            "transgressão quando o militar se utiliza, indevidamente, de violência (por exemplo, força "
            "física desnecessária) contra alguém que não esteja praticando uma infração penal (crime ou "
            "contravenção penal). O que se tutela nessa diferente interpretação é que o ato praticado "
            "pelo militar, mesmo que considerado violento, deve ser o necessário para vencer ou diminuir "
            "uma injusta reação ou agressão, pois caso o militar pratique um ato violento, sem justa "
            "causa, em face de uma pessoa que não está cometendo uma infração penal, estará configurada a "
            "transgressão em lide."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="VIII",
        natureza="grave",
        texto=(
            "divulgar ou contribuir para a divulgação de assunto de caráter sigiloso de que tenha "
            "conhecimento em razão do cargo ou função"
        ),
        comentario=(
            "A presente transgressão trata-se da violação de sigilo funcional do militar que deva, "
            "especialmente em situações que redundem em cautela para com informações e documentos "
            "classificados como sigilosos, guardar segredo daquilo que de qualquer modo saiba ou tenha "
            "presenciado. Agregada a tal conduta deve-se observar a situação funcional do militar, ou o "
            "cometimento da transgressão em razão desta, que divulgue ou contribua para a divulgação de "
            "assunto de caráter sigiloso. O verbo “divulgar” ou a expressão “contribuir para a "
            "divulgação” são condutas taxativas, ou seja, somente pode o militar ser responsabilizado "
            "pela presente transgressão disciplinar, se praticar uma ou as duas condutas descritas nos "
            "dois termos descritos. A conduta pode também configurar crimes militares previstos no art. "
            "324 e/ou 326 do CPM, ou constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="IX",
        natureza="grave",
        texto=(
            "utilizar-se de recursos humanos ou logísticos do Estado ou sob sua responsabilidade para "
            "satisfazer a interesses pessoais ou de terceiros"
        ),
        comentario=(
            "Para a configuração da presente transgressão, há necessidade de que a utilização do recurso "
            "público, ou sob a responsabilidade do Estado, seja para atender a interesses pessoais ou de "
            "terceiros. Não estando presente tal interesse, não há que se invocar a presente "
            "transgressão. Para sua configuração, não há necessidade da ocorrência de vantagem pessoal ou "
            "de terceiro, basta que a utilização dos meios logísticos tenha por finalidade a satisfação "
            "de interesse pessoal ou de terceiro. Destaca-se, ainda, que a utilização dos recursos "
            "estatais ou sob a responsabilidade da Administração Pública há de ser indevida, imoral, ou "
            "mesmo, ímproba. Comparando-se a transgressão acima com a do art. 13, inciso XIX, do CEDM, "
            "prevalecerá a mais específica. Não podem coexistir ambas num mesmo fato transgressivo. A "
            "conduta pode também configurar crimes previstos no CPM, relacionados com desvios de recursos "
            "e obtenção de vantagem indevida, além de atos de improbidade administrativa, ou pode também "
            "constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="X",
        natureza="grave",
        texto=(
            "exercer, em caráter privado, quando no serviço ativo, diretamente ou por interposta pessoa, "
            "atividade ou serviço cuja fiscalização caiba à Polícia Militar ou ao Corpo de Bombeiros "
            "Militar ou que se desenvolva em local sujeito à sua atuação"
        ),
        comentario=(
            "A presente transgressão se amolda aos típicos casos em que o militar, em caráter privado "
            "(remunerado ou não), atue em atividade ou serviço de responsabilidade ou fiscalização das "
            "IME, como, por exemplo: fiscal do meio ambiente, guarda de trânsito urbano ou rodoviário, "
            "elaboração de projetos de prevenção e combate a incêndio e pânico, instrutor na formação de "
            "brigadista ou bombeiro civil, como brigadista ou bombeiro civil, ou em outra situação "
            "congênere. O exercício de atividade ou serviço em lugar sujeito à atuação das IME se refere "
            "à situação de segunda atividade (“bico”) desenvolvida em lugar ou ambiente onde as IME podem "
            "atuar no exercício de sua missão constitucional. Nessa hipótese se enquadram o exercício da "
            "atividade de transporte clandestino de pessoas e/ou carga e de segurança privada armada ou "
            "não. O exercício do “bico” de segurança em estabelecimentos comerciais e industriais, "
            "boates, casas de espetáculos, restaurantes, farmácias, padarias, supermercados, agências "
            "prestadoras de serviço, condomínios abertos e fechados ou outros locais congêneres, ainda "
            "que o militar se encontre à paisana, de folga, férias, dispensado ou licenciado médico, "
            "caracteriza a transgressão disciplinar. Os demais casos de segunda atividade remunerada se "
            "amoldam à transgressão capitulada no art. 14, XIX, do CEDM, embora nem toda atividade "
            "paralela deva ser considerada uma conduta antiética ou infracional, devendo a autoridade "
            "militar competente avaliar, no caso concreto, a incompatibilidade, assiduidade, absenteísmo "
            "e o prejuízo para o serviço militar."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XI",
        natureza="grave",
        texto=(
            "maltratar ou permitir que se maltrate o preso ou a pessoa apreendida sob sua custódia ou "
            "deixar de tomar providências para garantir sua integridade física"
        ),
        comentario=(
            "Para configuração da presente transgressão, não há necessidade de haver lesão corporal ou "
            "qualquer outro resultado na pessoa presa ou apreendida, não requerendo nenhum outro "
            "resultado específico, a não ser a conduta ilícita de maltratar ou permitir que se maltrate o "
            "indivíduo. É o caso, por exemplo, do comandante de guarnição que assiste, passivamente, ao "
            "subordinado agredir a pessoa presa, apreendida, ou sob sua custódia. Em relação à conduta de "
            "deixar de tomar providência que garanta a integridade física do preso ou pessoa sob a "
            "custódia de militar, deve-se levar em consideração a exigibilidade de conduta diversa por "
            "parte do militar, pois se este não reunir condições (de segurança, por exemplo) para evitar "
            "que se maltrate o custodiado, não restará configurada a presente transgressão. A conduta "
            "pode também configurar crimes militares previstos nos artigos 181 (arrebatamento de presos), "
            "222 (constrangimento ilegal) e 333 (violência arbitrária) do CPM, bem como crimes comuns de "
            "abuso de autoridade ou mesmo tortura, além de poder ainda constituir transgressão "
            "disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XII",
        natureza="grave",
        texto=(
            "referir-se de modo depreciativo a outro militar, a autoridade e a ato da administração "
            "pública"
        ),
        comentario=(
            "A depreciação tem o sentido de diminuição de valor, de desconsideração e de desrespeito para "
            "com outro militar (mesmo que subordinado) ou autoridade (qualquer uma, mesmo as civis). No "
            "caso da depreciação a outro militar, esta pode ser exteriorizada por qualquer meio, a "
            "exemplo da carta anônima, blog, mensagem de e-mail, SMS, redes sociais ou também oralmente. "
            "Em relação a ato da Administração Pública, têm-se como exemplos, desde que contenham sentido "
            "pejorativo ou que indiquem circunstâncias indevidas, impertinentes e/ou desproporcionais, as "
            "referências contra a concessão de um reajuste salarial, alterações no plano de carreira, "
            "alteração do horário de expediente, além de mudanças nas regras de aposentadoria. "
            "Comparando-se a presente transgressão com as do art. 13, incisos I e V, do CEDM, prevalecerá "
            "a mais específica. Ademais, não podem coexistir ambas num mesmo fato transgressivo. A "
            "conduta pode também configurar crimes previstos no CPM (a exemplo dos que recaem contra a "
            "Autoridade ou Disciplina Militar e a honra), crime comum contra a honra, ou ainda constituir "
            "transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XIII",
        natureza="grave",
        texto=(
            "autorizar, promover ou tomar parte em manifestação ilícita contra ato de superior "
            "hierárquico ou contrário à disciplina militar"
        ),
        comentario=(
            "Os três verbos do período acima representam as formas de se cometer a referente "
            "transgressão, sendo, portanto, condutas taxativas e exaurientes. A manifestação há de ser "
            "ilegal, não autorizada, clandestina e sempre em desfavor de qualquer ato de superior "
            "hierárquico, ou contrário à disciplina militar. A conduta pode também configurar crimes "
            "previstos no CPM (a exemplo dos que recaem contra a Autoridade ou Disciplina Militar), ou "
            "ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XIV",
        natureza="grave",
        texto=(
            "agir de maneira parcial ou injusta quando da apreciação e avaliação de atos, no exercício de "
            "sua competência, causando prejuízo ou restringindo direito de qualquer pessoa"
        ),
        comentario=(
            "Além da ação de maneira parcial ou injusta, para que se configure a transgressão, requer-se "
            "uma conduta com resultado certo e determinado, ou seja, a ocorrência de prejuízo (econômico "
            "ou não) ou restrição de direito de qualquer pessoa (inclusive civil). Não havendo o "
            "resultado ou sendo a conduta interrompida antes que haja a produção do resultado, a conduta "
            "poderá, conforme o caso, constituir-se em outra transgressão disciplinar, a exemplo da "
            "prevista no art. 14, II, do CEDM, ou poderá ainda ser atípica."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XV",
        natureza="grave",
        texto="dormir em serviço",
        comentario=(
            "O tipo é claro e objetivo, não bastando para sua configuração nenhuma outra conduta que não "
            "a de dormir, mesmo que em um estado leve de sono. Dependendo das circunstâncias em que o "
            "militar for surpreendido dormindo em serviço, a conduta poderá configurar, também, o crime "
            "militar previsto no art. 203 do CPM (dormir em serviço), o qual requer, como elementar, a "
            "situação de estar o militar no serviço de sentinela, vigia ou, ainda, outra situação "
            "prevista no referido dispositivo legal. Por isso, infere-se que a transgressão disciplinar "
            "constitui-se numa conduta muito mais ampla do que o crime militar, bastando, pois, para sua "
            "configuração, que o transgressor esteja em qualquer situação de serviço, tais como: durante "
            "instrução e expediente de serviço, salvo em situações devidamente autorizadas. Devido às "
            "circunstâncias que envolvem o ato de dormir, sugere-se, sempre que possível, além do militar "
            "que se deparar com a situação, que outros meios de provas sejam produzidos para evidenciar a "
            "conduta transgressiva (ex: filmagem, foto, acionamento de testemunhas etc)."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XVI",
        natureza="grave",
        texto="retardar ou deixar de praticar, indevidamente, ato de ofício",
        comentario=(
            "Retardar quer dizer fazer com atraso, adiar, tornar mais lento. Nessa circunstância, o "
            "transgressor pratica o ato de ofício fora de um lapso temporal razoável. Deixar de praticar "
            "significa dizer que o transgressor foi omisso, não agiu quando assim deveria fazê-lo. A "
            "expressão “indevidamente” deve ser entendida como falta de amparo legal para retardar ou "
            "deixar de praticar o ato de ofício. O “ato de ofício” retrata um ato de dever funcional, "
            "obrigatório, que não carece, para sua realização, de determinação de autoridade, podendo-se "
            "citar como exemplo os artigos 243 do Código de Processo Penal Militar (CPPM) e 302 do Código "
            "de Processo Penal (CPP), os quais estabelecem que as autoridades devam prender quem estiver "
            "em flagrante delito de infração penal. Considerando o caso concreto e a possibilidade "
            "aparente de conflito desse tipo com o art. 14, incisos III ou XV, do CEDM, prevalecerá o "
            "mais específico. A transação, comércio, cessão, troca, empréstimo, doação, porte e posse, de "
            "forma ilegal, de arma de fogo, munição ou colete, além do eventual crime comum previsto na "
            "Lei 10.826/03, importará ao militar responder pela transgressão contida no tipo acima, "
            "podendo ainda, conforme as circunstâncias do fato (ex: arma com numeração "
            "raspada/adulterada/sem numeração, tráfico, contrabando, descaminho, furto, roubo, peculato, "
            "receptação etc), servir de motivação para sua submissão a PAD/PADS, com fulcro no art. 64, "
            "II (ou 34, II), do CEDM. A conduta pode também configurar crimes previstos no art. 319 "
            "(prevaricação) e/ou 322 (condescendência criminosa) do CPM, ou ainda constituir transgressão "
            "disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XVII",
        natureza="grave",
        texto="negar publicidade a ato oficial",
        comentario=(
            "Um dos princípios norteadores do processo e dos atos administrativos é o da publicidade, "
            "descrito no caput do art. 37 da CRFB, que se materializa pela publicação do ato em Boletim "
            "ou Diário Oficial, para conhecimento do público em geral. A regra, pois, é que a publicidade "
            "somente poderá ser excepcionada quando a defesa da intimidade ou interesse social o "
            "exigirem. Amolda-se à conduta, por exemplo, o militar que nega a publicidade de atos sobre "
            "licitações e contratos administrativos. Ressalta-se que a negativa de publicidade há de ser "
            "imotivada, pois, caso contrário, não incide a presente transgressão."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XVIII",
        natureza="grave",
        texto=(
            "induzir ou instigar alguém a prestar declaração falsa em procedimento penal, civil ou "
            "administrativo ou ameaçá-lo para que o faça"
        ),
        comentario=(
            "Visa a referida transgressão preservar a prova, para a busca da verdade real. Seu "
            "cometimento dar-se-á por meio do induzimento, instigação ou ameaça, ao propósito de que "
            "qualquer pessoa (testemunha, vítima, coautor ou partícipe) preste declaração falsa em "
            "procedimento penal, civil ou administrativo. “Induzir” significa suscitar, fazer surgir uma "
            "ideia inexistente; “instigar”; significa animar, estimular, reforçar uma ideia existente. "
            "“Ameaçar” trata-se de prometer, ostensiva ou veladamente, um mal injusto, capaz de incutir "
            "medo em alguém. Caso o induzimento ou a instigação de testemunha se dê por meio de dinheiro "
            "ou qualquer outra vantagem, a conduta poderá também se caracterizar como crime previsto no "
            "art. 347 do CPM (corrupção ativa de testemunha, perito ou intérprete). Já no caso de ameaça, "
            "poderá também configurar o crime descrito no art. 342 do CPM (coação). Em qualquer dos dois "
            "casos, pode ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XIX",
        natureza="grave",
        texto=(
            "fazer uso do posto ou da graduação para obter ou permitir que terceiros obtenham vantagem "
            "pecuniária indevida"
        ),
        comentario=(
            "A vantagem indevida pessoal ou de terceiro há de ser pecuniária, ou seja, apreciável "
            "economicamente, não sendo, necessariamente, a vantagem em dinheiro. Para a configuração do "
            "tipo transgressivo em comento, não há necessidade de que o militar ou terceiro obtenha a "
            "vantagem pecuniária indevida, basta que o militar faça uso do posto ou da graduação com essa "
            "finalidade. A conduta pode também configurar crimes militares previstos no art. 308, § 2º "
            "(corrupção passiva privilegiada) ou 334 (patrocínio indébito) do CPM, ou ainda constituir "
            "transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=13,
        inciso="XX",
        natureza="grave",
        texto="faltar ao serviço",
        comentario=(
            "Para a configuração da transgressão, o serviço para o qual o militar faltou deve estar "
            "previsto em escala antecipada ou por ordem emanada por quem de direito. Os artigos 14 e 15 "
            "da Lei n. 5.301/69, que contém o Estatuto dos Militares do Estado de Minas Gerais (EMEMG), "
            "asseveram que a função policial militar é exercida por oficiais e praças da Polícia Militar, "
            "com a finalidade de preservar, manter e restabelecer a ordem pública e segurança interna, "
            "através das várias ações policiais ou militares, em todo o território do Estado. Nos mesmos "
            "dispositivos legais, assevera-se que, a qualquer hora do dia ou da noite, na sede da Unidade "
            "ou onde o serviço o exigir, o militar deve estar pronto para cumprir a missão que lhe for "
            "confiada pelos seus superiores hierárquicos ou impostos pelas leis e regulamentos. Por isso, "
            "a importância do cumprimento das escalas de serviço. No caso em que as faltas ao serviço "
            "ensejarem o crime de deserção, além das providências de polícia judiciária militar dispostas "
            "no CPPM, o aspecto disciplinar residual deverá ser apurado em sede de PAD/PADS, conforme se "
            "depreende do art. 240-A do EMEMG, cuja instauração se dará com fulcro no art. 64, II (ou 34, "
            "II), c/c o art. 13, III, do CEDM, além de outros tipos transgressivos que poderão surgir no "
            "caso concreto. A ausência do militar ao treinamento policial/profissional básico (TPB) "
            "constituirá a presente transgressão, posto que estará à disposição dessa atividade. "
            "Aclara-se que comete a presente transgressão o militar que falta à escala para o cumprimento "
            "da sanção de prestação de serviço (art. 24, III, do CEDM)."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="I",
        natureza="média",
        texto="executar atividades particulares durante o serviço",
        comentario=(
            "Tal transgressão decorre da prática de ato estranho ao interesse do serviço, ou seja, "
            "revestindo-se de uma natureza ou finalidade eminentemente particular e que não "
            "necessariamente traga prejuízo ao serviço público."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="II",
        natureza="média",
        texto=(
            "demonstrar desídia no desempenho das funções, caracterizada por fato que revele desempenho "
            "insuficiente, desconhecimento da missão, afastamento injustificado do local ou procedimento "
            "contrário às normas legais, regulamentares e a documentos normativos, administrativos ou "
            "operacionais"
        ),
        comentario=(
            "Para a configuração da transgressão em análise, é imprescindível que seja demonstrada a "
            "desídia no exercício funcional, caracterizada por fato que revele, pelo menos, uma das "
            "quatro condutas descritas no tipo. Nesses termos, devem estar presentes na conduta do "
            "militar todos os seus elementos constitutivos, a saber: 1. Conduta desidiosa. Desídia possui "
            "múltiplos significados, dentre eles, preguiça, desleixo, inércia, descaso, incúria, "
            "desatenção, negligência, indolência, apatia e outros; 2. A situação funcional caracterizada "
            "pelo “desempenho das funções”. No instante do cometimento da transgressão, deverá o militar "
            "estar de serviço ou deve a transgressão ser cometida em razão de sua função policial ou "
            "bombeiro militar; 3. Desempenho insuficiente: refere-se ao cumprimento de atribuições ou "
            "ordens, de forma a não satisfazer por completo aquilo que fora previamente determinado. Para "
            "a ocorrência desse elemento, deve preexistir uma atribuição determinada, que seja "
            "objetivamente mal desempenhada; 4. Desconhecimento da missão: caracteriza-se pela falta de "
            "informações, por parte do militar, acerca da tarefa que lhe foi incumbida e da qual deveria "
            "inteirar-se para o fiel e efetivo cumprimento; 5. Afastamento injustificado do local: "
            "configura-se pela falta de razões plausíveis que possam escudar seu afastamento, sem "
            "autorização, do lugar onde deveria estar. Acrescenta-se que, dependendo da situação, poderá "
            "configurar, também, o crime previsto no art. 195 CPM (abandono de posto); 6. Procedimento "
            "contrário às normas legais, regulamentares e a documentos normativos, administrativos ou "
            "operacionais: é fundamental a identificação da norma violada como aquelas de cunho genérico, "
            "emanadas por meio de memorando, ofício circular, instrução ou outro documento interno "
            "correlato que, neste caso, deverá ser mencionado no termo de abertura de vista, para "
            "apresentação de defesa."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="III",
        natureza="média",
        texto=(
            "deixar de cumprir ordem legal ou atribuir a outrem, fora dos casos previstos em lei, o "
            "desempenho de atividade que lhe competir"
        ),
        comentario=(
            "A primeira conduta consiste na omissão em cumprir qualquer ordem (mesmo verbal) legal ou que "
            "não contrarie uma lei, norma ou princípios da Administração Pública. Para o cometimento da "
            "primeira figura transgressiva, não há necessidade de que a ordem seja de natureza pessoal e "
            "direcionada a militar determinado, podendo ser, inclusive, aquelas de cunho genérico, "
            "emanadas por meio de memorando, ofício circular, instrução ou outro documento interno "
            "correlato que, neste caso, deverá ser mencionado no termo de abertura de vista para "
            "apresentação de defesa. Diferencia-se da transgressão contida no art. 14, II, do CEDM, posto "
            "que nesta o descumprimento da norma está ligado ao desempenho das funções. Acrescenta-se que "
            "a ordem legal descumprida, no caso ora analisado, não necessariamente tem de estar "
            "respaldada em norma, bastando que não contrarie os princípios descritos no art. 37 da "
            "CRFB/88, bem como outros que regem a Administração Pública. A conduta transgressiva de falta "
            "à instrução (semanal, de tiro, de educação física ou outras), que seja parte do empenho "
            "previsto, não deve ser considerada falta ao serviço (art. 13, XX, do CEDM), mas sim "
            "descumprimento de ordem, prevista no art. 14, III, do CEDM. Por sua vez, o atraso "
            "injustificado para a atividade se enquadra no art. 15, I, do CEDM. A ausência do militar ao "
            "treinamento policial/profissional básico (TPB) constituirá a transgressão descrita no art. "
            "13, XX, do CEDM, posto que ele estará à disposição dessa atividade. A ausência do militar "
            "apenas à instrução pré-turno constituirá a transgressão do art. 15, I, do CEDM, já que "
            "acarretará atraso ao serviço operacional. A segunda figura do tipo transgressivo consiste em "
            "atribuir a outra pessoa (militar ou civil) tarefa, missão, função ou cargo que lhe caiba, "
            "estando patente a intenção do transgressor em se esquivar (evitar, fugir, até mesmo tentar "
            "ludibriar) de sua responsabilidade. Considerando o caso concreto e a possibilidade aparente "
            "de conflito desse tipo com o art. 13, XVI ou art. 14, XV, do CEDM, prevalecerá o mais "
            "específico. A conduta pode também configurar crimes militares previstos nos artigos 149 "
            "(motim), 163 (recusa de obediência), 164 (oposição de ordem de sentinela), 196 "
            "(descumprimento da missão) ou 301 (desobediência a ordem de autoridade militar) do CPM, ou "
            "ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="IV",
        natureza="média",
        texto="assumir compromisso em nome da IME ou representá-la indevidamente",
        comentario=(
            "O órgão de representação da IME é o Comando-Geral e as demais unidades administrativas e "
            "operacionais das Instituições são representadas por seus respectivos Comandantes, Diretores "
            "ou Chefes. Somente mediante expressa autorização da autoridade competente, poderão outros "
            "oficiais e praças assumir compromisso em nome da Instituição ou representá-la para "
            "determinado fim. O compromisso e a representação mencionados na transgressão referem-se às "
            "situações em que a IME ou Unidade é representada por algum militar que não possua "
            "legitimidade para tal. Não necessita, para sua configuração, da presença de nenhum resultado "
            "que crie ou não assegure direitos ou obrigações, bastando o compromisso ou a representação "
            "indevida da Instituição. A conduta pode também configurar crimes militares previstos no art. "
            "167 (assunção de comando sem ordem ou autorização) ou 335 (usurpação de função) do CPM ou "
            "ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="V",
        natureza="média",
        texto="usar indevidamente prerrogativa inerente a integrante das IME",
        comentario=(
            "A aludida transgressão se refere, por exemplo, às situações em que o militar se faz passar "
            "por grau hierárquico ou função que não possui, tais como Comandante, Coordenador, Sentinela, "
            "e até mesmo por algum encargo do qual não foi legitimamente investido. Para a configuração "
            "da transgressão, não há a necessidade de se auferir qualquer vantagem. A conduta pode também "
            "configurar crimes militares previstos nos artigos 167 (assunção de comando sem ordem ou "
            "autorização), 171 (uso indevido de uniforme, distintivo ou insígnia), ou 335 (usurpação de "
            "função) do CPM ou ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="VI",
        natureza="média",
        texto="descumprir norma técnica de utilização e manuseio de armamento ou equipamento",
        comentario=(
            "Constitui-se a falta na inobservância à norma específica de utilização e manuseio de "
            "armamento e equipamento policial ou atinente à atividade bombeiro militar (até mesmo a "
            "viatura e aparelhos de comunicação). O conceito de norma técnica deve ser entendido como "
            "qualquer tipo de norma específica que cuide da correta forma de utilização e manuseio de "
            "armamento e equipamento policial/bombeiro militar, como o Manual de Armamento Convencional, "
            "o Manual de Prática Policial, os Cadernos Doutrinários, a Resolução interna que dispõe sobre "
            "a aquisição, o registro, o cadastro e o porte de arma de fogo de propriedade do militar e o "
            "porte de arma de fogo pertencente à IME, Notas Instrutivas ou outras normas que porventura "
            "vierem a disciplinar a presente matéria, até mesmo o manual do fabricante, na ausência de "
            "norma editada pela instituição militar. Trata-se de norma transgressiva em branco, cuja "
            "aplicação requer um complemento, ou seja, a indicação da norma técnica violada pelo militar, "
            "que deverá vir expressa na notificação para apresentação de defesa prévia e/ou no termo de "
            "abertura de vista. Como exemplos, podem-se citar: manuseio de armamento fora do local "
            "apropriado; disparo acidental de arma de fogo; acomodação irregular de coletes balísticos ou "
            "outros armamentos e equipamentos. Ressalvado o disposto no art. 5º, §16º, desta Instrução, o "
            "descumprimento a qualquer preceito de instrumento normativo interno, que regule a aquisição, "
            "registro, cadastro, controle interno e porte de arma de fogo de armamento da carga ou "
            "particular, de origem lícita, configura-se a transgressão em comento. A conduta pode também "
            "configurar crimes previstos na Lei n. 10.826/03, em especial, nos artigos 13 (omissão de "
            "cautela) ou 15 (disparo de arma de fogo), ou ainda constituir transgressão disciplinar "
            "residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="VII",
        natureza="média",
        texto=(
            "faltar com a verdade, na condição de testemunha, ou omitir fato do qual tenha conhecimento, "
            "assegurado o exercício constitucional da ampla defesa"
        ),
        comentario=(
            "É uma transgressão própria, uma vez que somente a testemunha pode cometê-la. Pode ser "
            "manifesta de duas maneiras distintas, sendo a primeira a praticada pela mentira ou inverdade "
            "e, a segunda, pela omissão de fato de que tenha conhecimento. O dever de dizer a verdade, na "
            "condição de testemunha, abarca inclusive as situações em que o militar presta o falso "
            "testemunho em processos de qualquer natureza. Para a correta imputação da falta, deve-se "
            "propiciar à testemunha o direito constitucional à ampla defesa, contraditório e o "
            "consequente devido processo legal, preferencialmente em autos apartados, nos quais figurará "
            "como acusado e não mais como testemunha. A conduta pode também configurar crime previsto no "
            "art. 346 do CPM ou no art. 342 do CP (falso testemunho ou falsa perícia) ou ainda constituir "
            "transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="VIII",
        natureza="média",
        texto=(
            "deixar de providenciar medida contra irregularidade de que venha a tomar conhecimento ou "
            "esquivar-se de tomar providências a respeito de ocorrência no âmbito de suas atribuições"
        ),
        comentario=(
            "Cuida a presente transgressão da importância de se manter o dever funcional de agir ou tomar "
            "as providências pertinentes que a situação exigir, se desdobrando em duas condutas "
            "distintas: deixar de tomar providências ou esquivar-se de tomá-la, em face de qualquer tipo "
            "de irregularidade de que venha a presenciar ou conhecer. A conduta pode também configurar "
            "crimes militares previstos no art. 319 (prevaricação) ou no art. 322 (condescendência "
            "criminosa) do CPM, ou ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="IX",
        natureza="média",
        texto=(
            "utilizar-se do anonimato ou envolver indevidamente o nome de outrem para esquivar-se de "
            "responsabilidade"
        ),
        comentario=(
            "A primeira forma de se configurar a presente transgressão é pelo anonimato, o que é defeso "
            "pela própria Constituição Federal, em seu art. 5º, IV (“É livre a manifestação de "
            "pensamento, sendo vedado o anonimato”). A segunda forma de se configurar a transgressão é o "
            "indevido envolvimento do nome de outra pessoa, seja ela militar ou civil, para se esquivar "
            "de responsabilidade. A conduta pode também configurar crimes militares previstos nos artigos "
            "214 (calúnia), 215 (difamação), 216 (Injúria), ou 343 (denunciação caluniosa) do CPM, ou "
            "ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="X",
        natureza="média",
        texto=(
            "danificar ou inutilizar, por uso indevido, negligência, imprudência ou imperícia, bem da "
            "administração pública de que tenha posse, ou seja, detentor"
        ),
        comentario=(
            "O significado de “bem” abrange todas as coisas corpóreas ou incorpóreas, suscetíveis de "
            "valor econômico. “Danificar” compreende a conduta de destruir, deteriorar ou fazer "
            "desaparecer algum bem, ao passo que “inutilizar” significa tornar imprestável ou inservível. "
            "Configura a presente transgressão qualquer espécie de danificação ou inutilização, mesmo que "
            "estas se deem por culpa (negligência, imprudência ou imperícia) do militar, uma vez que este "
            "possui o dever de bem cuidar e administrar os bens públicos. Para fins do cometimento dessa "
            "transgressão, o bem da Administração Pública ora referido deve ser entendido como sendo não "
            "somente aquele pertencente ao patrimônio da Administração, mas também aquele que esteja sob "
            "sua posse, guarda ou detenção, a exemplo da frota terceirizada de viaturas. A conduta pode "
            "também configurar crimes militares previstos no Capítulo VII do Título V do CPM (“Do Dano”), "
            "ou ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XI",
        natureza="média",
        texto=(
            "deixar de observar preceito legal referente a tratamento, sinais de respeito e honras "
            "militares, definidos em normas especificas"
        ),
        comentario=(
            "Tal transgressão se refere essencialmente às normas alusivas à inobservância de regras de "
            "tratamento (a necessidade de se referir a um superior por senhor(a), a uma autoridade, por "
            "vossa excelência, dependendo do caso); sinais de respeito e honras militares (continência "
            "individual, continência à bandeira, ao hino nacional e outros). As normas específicas a que "
            "faz alusão o presente inciso podem ser previstas em quaisquer documentos normativos, "
            "mormente o Regulamento de Continências, sem prejuízo para os memorandos, avisos, resoluções "
            "e os demais documentos previstos em normas próprias das IME, que disciplinem ou que venham a "
            "disciplinar a matéria. Trata-se de norma transgressional em branco, cuja aplicação requer um "
            "complemento, ou seja, a indicação da norma específica inobservada pelo militar, que deverá "
            "vir expressa na notificação para apresentação de defesa prévia e/ou no termo de abertura de "
            "vista."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XII",
        natureza="média",
        texto=(
            "contribuir para a desarmonia entre os integrantes das respectivas IMEs, por meio da "
            "divulgação de notícia, comentário ou comunicação infundados"
        ),
        comentario=(
            "O presente preceito visa tutelar a camaradagem e o espírito de cooperação previstos no art. "
            "9º, inciso VII, do CEDM. Para a configuração de tal transgressão, basta que a divulgação de "
            "notícia, comentário ou comunicação infundados se revistam de potencial ofensivo à harmonia "
            "entre os militares. A conduta pode também configurar crimes militares previstos no art. 214 "
            "(calúnia) ou 343 (denunciação caluniosa) do CPM, ou ainda constituir transgressão "
            "disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XIII",
        natureza="média",
        texto="manter indevidamente em seu poder bem de terceiro ou da Fazenda Pública",
        comentario=(
            "A expressão “bem” se refere a qualquer material da Administração Pública ou de terceiro, "
            "seja ele militar ou civil. Tal transgressão se caracteriza pela posse ilegítima, mesmo que "
            "temporária, de qualquer bem público ou particular. Como exemplo, citam-se os casos em que o "
            "militar, não estando devidamente autorizado pelo comando, permanece, por conta própria, com "
            "equipamento público (TV, DVD, computador ou qualquer outro), ou que mantenha consigo um "
            "objeto de terceiro apreendido em uma operação, mesmo que não venha a utilizá-lo. Para fins "
            "do cometimento da presente transgressão, o bem da Administração Pública ora referido, deve "
            "ser entendido como sendo não somente aqueles pertencentes ao patrimônio da Administração, "
            "mas também aqueles que estejam sob sua posse, guarda ou detenção. A conduta pode também "
            "configurar crimes militares previstos nos artigos 241 (furto de uso), 248 (apropriação "
            "indébita), 249 (apropriação de coisa havida acidentalmente ou achada) ou 303 (peculato) do "
            "CPM, ou ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XIV",
        natureza="média",
        texto="maltratar ou não ter o devido cuidado com os bens semoventes das IME",
        comentario=(
            "A presente transgressão se refere especificamente à falta de cuidado com os animais equinos "
            "e cães empregados na Instituição, em apoio às atividades policiais e de bombeiros de "
            "natureza militar. A conduta pode também configurar crime ambiental previsto no art. 32 da "
            "Lei 9.605/98 ou, resultando morte ao animal, crimes previstos no Capítulo VII do Título V do "
            "CPM (“Do Dano”), ou ainda constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XV",
        natureza="média",
        texto="deixar de observar prazos regulamentares",
        comentario=(
            "A presente transgressão cuida do dever de presteza e pontualidade na conclusão e no "
            "desenvolvimento de atividades, mormente na elaboração de processos e procedimentos "
            "administrativos, de natureza disciplinar ou não, como por exemplo, a conclusão de uma "
            "Sindicância ou de um IPM. Não se confunde, todavia, com o retardamento imotivado do "
            "cumprimento de uma ordem legal, como por exemplo, a tardia entrega de um relatório, boletim "
            "de ocorrências ou ainda um estudo recomendado pelo comandante ou chefe, cujos prazos não são "
            "regulamentados. Nesses casos, ocorre a violação do inciso V do art. 15 do CEDM e não a do "
            "tipo em comento. Amolda-se também à presente transgressão, a conduta do militar que deixa de "
            "entregar os autos à Administração Militar ou ao Encarregado, após o término do prazo legal. "
            "Trata-se de transgressão disciplinar permanente, ou seja, aquela que se renova a cada dia em "
            "que o documento está em atraso na posse do militar, sem que haja a sua devolução. Nesses "
            "termos, a data da devolução será considerada a data da falta, para fins do cômputo do prazo "
            "da prescrição da pretensão punitiva. A conduta pode também configurar crime militar previsto "
            "nos artigos 196 (descumprimento da missão), 319 (prevaricação) ou 324 do CPM (inobservância "
            "de lei, regulamento ou instrução) ou constituir transgressão disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XVI",
        natureza="média",
        texto=(
            "comparecer fardado a manifestação ou reunião de caráter político partidário, exceto a "
            "serviço"
        ),
        comentario=(
            "A transgressão se refere ao dever de isenção e imparcialidade a que os integrantes das IME "
            "devem observar. Esse tipo deriva da Lei Estadual n. 5.301/69, que contém o Estatuto dos "
            "Militares Estaduais de Minas Gerais (EMEMG), mormente os artigos 23 e 30. Caso algum "
            "militar, não estando de serviço, compareça fardado a reuniões políticopartidárias, pode "
            "denotar o entendimento de que a Polícia Militar ou o Corpo de Bombeiros Militar está "
            "apoiando e/ou defendendo as ideias de determinado partido ou ideologia política, o que "
            "caracterizaria a transgressão disciplinar mencionada no referido tipo."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XVII",
        natureza="média",
        texto="recusar-se a identificar-se quando justificadamente solicitado",
        comentario=(
            "Ressalta-se que a exigência de identificação deve ser justificada por pessoa legalmente "
            "investida de cargo ou função pública, sempre em razão desta, podendo partir de um integrante "
            "das Forças Armadas, Poder Judiciário, Polícia Civil, Federal, Corpo de Bombeiros Militar, "
            "Polícia Militar ou outro órgão público qualquer. Nos casos em que o militar recusar a se "
            "identificar a autoridade civil, quando legalmente solicitado, a conduta poderá configurar, "
            "também, a contravenção penal prevista no art. 68 do Decreto-Lei n. 3688/41. Em se tratando "
            "de autoridade militar, a conduta pode também configurar crimes militares previstos no art. "
            "163 (recusa de obediência) ou 301 (desobediência) do CPM ou ainda constituir transgressão "
            "disciplinar residual."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XVIII",
        natureza="média",
        texto=(
            "não portar etiqueta de identificação quando em serviço, salvo se previamente autorizado, em "
            "operações policiais específicas"
        ),
        comentario=(
            "A norma tutela o dever de lisura e transparência das ações a que devem os militares seguir, "
            "como, por exemplo, a garantia constitucional de todo preso ter direito à identificação dos "
            "responsáveis por sua prisão (art. 5º, LXIV, CR/88). A etiqueta de identificação deve estar "
            "no seu devido lugar, conforme normas específicas de apresentação pessoal, ou seja, "
            "propiciando a boa visibilidade e a consequente identificação do militar, quando em serviço. "
            "Guardar, por exemplo, a etiqueta de identificação dentro do bolso configura a presente "
            "transgressão. Somente em operações específicas, e mediante expressa autorização, estará o "
            "militar autorizado a não portar etiqueta de identificação. Não estando o militar em serviço, "
            "configura-se a transgressão capitulada no inciso II do artigo 15 do CEDM."
        ),
    ),
    Transgressao(
        artigo=14,
        inciso="XIX",
        natureza="média",
        texto=(
            "participar, o militar da ativa, de firma comercial ou de empresa industrial de qualquer "
            "natureza, ou nelas exercer função ou emprego remunerado"
        ),
        comentario=(
            "Com fulcro no art. 42 c/c o art. 142, §3º, X, da CF/88, os integrantes das Polícias "
            "Militares e Corpos de Bombeiros Militares são militares dos Estados, sendo que lei disporá "
            "sobre as situações especiais dos militares, consideradas as peculiaridades de suas "
            "atividades. Assim, o art. 15 do EMEMG impõe que a qualquer hora do dia ou da noite, na sede "
            "da Unidade ou onde o serviço o exigir, o militar do Estado deve estar pronto para cumprir a "
            "sua missão. Nesse mister, dispõe o art. 22 do EMEMG e o art. 8º da Lei n. 14.130/2001 as "
            "seguintes regras: EMEMG: Art. 22 - Aos militares da ativa é vedado fazer parte de firmas "
            "comerciais, de empresas industriais de qualquer natureza ou nelas exercer função ou emprego "
            "remunerado. [...] § 2º - Os militares da ativa podem exercer, diretamente, a gestão de seus "
            "bens desde que não infrinjam o disposto no presente artigo. § 3º - No intuito de desenvolver "
            "a prática profissional e elevar o nível cultural dos elementos da Corporação, é permitido, "
            "no meio civil, aos militares titulados, o exercício do magistério ou de atividades "
            "técnicoprofissionais, atendidas as restrições previstas em lei própria. Lei n. 14.130/2001: "
            "Art. 8º – Fica proibido ao militar da ativa ser proprietário ou consultor de empresa de "
            "projeto, comercialização, instalação, manutenção e conservação nas áreas de prevenção e "
            "combate a incêndio e pânico. Conforme os dispositivos acima, é permitido aos militares "
            "titulados o exercício de atividade de magistério e técnico-profissionais, desde que não se "
            "enquadre como proprietário ou consultor de empresa de projeto, comercialização, instalação, "
            "manutenção e conservação nas áreas de prevenção e combate a incêndio e pânico ou outras "
            "restrições previstas em lei. O regramento objetiva tutelar a saúde do militar, dando "
            "condições para seu restabelecimento físico e mental após jornada regular de trabalho nas "
            "IME, que seria mais difícil, caso viesse a desempenhar atividades que não lhe propiciasse "
            "descanso, além de causar sérios prejuízos ao militar e à Instituição. A configuração da "
            "transgressão não exige que a atividade remunerada gere algum vínculo empregatício ou direito "
            "trabalhista. Ressalta-se que exercício de atividade de segurança privada e de transporte "
            "clandestino de pessoas e/ou carga devem se enquadrar na transgressão descrita no art. 13, X, "
            "do CEDM."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="I",
        natureza="leve",
        texto="chegar injustificadamente atrasado para qualquer ato de serviço de que deva participar",
        comentario=(
            "O objetivo primordial da transgressão acima descrita é preservar a pontualidade e a "
            "assiduidade do militar, que é regido por normas próprias, calcadas basicamente pela "
            "hierarquia, disciplina e pelo dever constitucional de eficiência. O atraso injustificado é "
            "considerado transgressão disciplinar, uma vez que o militar deve, obrigatoriamente, "
            "organizar-se, além de se preparar para o desempenho de suas atividades funcionais. O horário "
            "da chamada ou do início do serviço deve ser disposto de modo preciso e enfático, por meio de "
            "escala ou por uma ordem (mesmo que verbal) prévia para o serviço. Em conformidade com a "
            "Resolução que trata da jornada de trabalho no Corpo de Bombeiros Militar e na Polícia "
            "Militar, que tem a chamada para todos os turnos operacionais (“chamada pré-turno”), esta se "
            "dará 30 (trinta) minutos antes do lançamento, para fins do treinamento tático, sendo o "
            "atraso computado a partir da aludida chamada."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="II",
        natureza="leve",
        texto=(
            "deixar de observar norma específica de apresentação pessoal definida em regulamentação "
            "própria"
        ),
        comentario=(
            "Trata-se de norma transgressiva em branco, cuja aplicação requer um complemento, ou seja, a "
            "indicação da norma de apresentação pessoal violada pelo militar, que deverá vir expressa na "
            "notificação para apresentação de defesa prévia e/ou no termo de abertura de vista. As normas "
            "específicas de apresentação pessoal estão descritas no Regulamento de Uniformes e Insígnias "
            "da Polícia Militar (RUIPM) e do Corpo de Bombeiros Militar (RUICBM), sem prejuízo para os "
            "demais documentos normativos que porventura disciplinem ou venham a disciplinar a matéria, a "
            "exemplo das Notas Instrutivas ou documentos similares que regulam as especificações técnicas "
            "de fabricação de fardamento ou equipamentos. O comparecimento de militar em trajes civis nas "
            "dependências das IME, nas situações previstas no RUIPM e RUICBM, deverá ocorrer de forma "
            "condizente com o local e atividade a ser exercida."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="III",
        natureza="leve",
        texto="deixar de observar princípios de boa educação e correção de atitudes",
        comentario=(
            "Não houve uma descrição objetiva de quais sejam os princípios de boa educação e correção de "
            "atitudes, cabendo, destarte, aos aplicadores do CEDM adequá-los ao caso concreto. Todavia, "
            "embora não descritas legalmente, a boa educação e a correção de atitudes derivam de um dever "
            "ético e social ligado à moral e aos bons costumes, exigindo-se que o militar estadual se "
            "porte de modo discreto, cortês, garantidor e promotor dos direitos humanos e, sobretudo, de "
            "modo conveniente. Alguns princípios da ética militar podem ser invocados para sustentar a "
            "falta epigrafada, como, por exemplo, os incisos VII, VIII, X e XII do art. 9º do CEDM, o que "
            "reforça a ideia de que a boa educação e a correção de atitudes são predicados essenciais ao "
            "militar estadual, que deve ser considerado um referencial no meio social. Para a "
            "configuração da transgressão em análise, nas situações da vida particular do militar, a "
            "conduta praticada deve causar reflexos negativos para a IME, o que será avaliado por meio de "
            "um ponderado senso de razoabilidade. Amolda-se ao presente tipo, por exemplo, a situação em "
            "que o militar fardado é encontrado em via pública ou lugar acessível a esta, ingerindo "
            "bebida alcoólica (afora eventos de confraternizações e/ou congraçamentos em áreas sujeitas à "
            "Administração Militar em que a prática moderada pode ser tolerada) e não apresenta sinais de "
            "embriaguez."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="IV",
        natureza="leve",
        texto=(
            "entrar ou tentar entrar em repartição ou acessar ou tentar acessar qualquer sistema "
            "informatizado, de dados ou de proteção, para o qual não esteja autorizado"
        ),
        comentario=(
            "O presente tipo prevê diversas condutas que devem ser analisadas individualmente: – Entrar "
            "em repartição para a qual não esteja autorizado; – Tentar entrar em repartição para a qual "
            "não esteja autorizado; – Acessar qualquer sistema informatizado, de dados ou de proteção, "
            "para o qual não esteja autorizado; – Tentar acessar qualquer sistema informatizado, de dados "
            "ou de proteção, para o qual não esteja autorizado. Para os fins do presente artigo, "
            "consideram-se os seguintes conceitos: a) Repartição - qualquer sala ou dependência física de "
            "área sujeita à Administração Militar. b) Sistema informatizado - conjunto de partes "
            "interagentes e interdependentes que, utilizando-se da ciência e da tecnologia, realiza o "
            "armazenamento e o tratamento da informação, mediante a utilização de equipamentos e "
            "procedimentos da área de processamento de dados (ex: Sistema Informatizado de Recursos "
            "Humanos – SIRH/PM ou Sistema Informatizado de Gestão de Pessoas - SIGP/BM). c) Sistema de "
            "dados - conjunto que contenha qualquer representação de fatos, situações, comunicações, "
            "notícias, documentos, extratos de documentos, fotografias, gravações, relatos, denúncias, ou "
            "fatos de interesse da entidade, que formem um todo unitário, com determinado objetivo "
            "traçado pela instituição (ex: Sistema de Controle de Atendimento e Despacho - CAD). d) "
            "Sistema de proteção - conjunto de partes interligadas que formam um todo unitário, com o "
            "objetivo de realizar a salvaguarda de determinados conjuntos de saberes, sejam eles dados, "
            "conhecimentos, ou equipamentos que, via de regra, exigem para o seu acesso senhas ou "
            "autorizações específicas a determinadas pessoas, rigorosamente selecionadas (ex: Sistema de "
            "Informações de Segurança Pública - INFOSEG). Para a configuração da transgressão não há "
            "necessidade da ocorrência de nenhum outro resultado específico, como o de divulgar ou "
            "adulterar o contido nos dados (o que pode ser tipificado no art. 13, VIII, do CEDM, por "
            "exemplo), bastando simplesmente a tentativa ou a entrada na repartição; a tentativa ou o "
            "acesso ao sistema, para os quais não esteja autorizado."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="V",
        natureza="leve",
        texto="retardar injustificadamente o cumprimento de ordem ou o exercício de atribuição",
        comentario=(
            "Conforme comentários insertos no art. 14, III, do CEDM, não há necessidade de que a ordem "
            "seja de natureza pessoal e direcionada a militar determinado, podendo ser, inclusive, "
            "aquelas de cunho genérico, emanadas por meio de memorando, ofício circular, instrução ou "
            "outro documento interno correlato que, neste caso, deverá ser mencionado no termo de "
            "abertura de vista, para apresentação de defesa. Na transgressão acima, o que se deve levar "
            "em conta é a legalidade da ordem e do exercício da atribuição. Ressalta-se que a ordem e/ou "
            "a atribuição devem ser cumpridas, entretanto, de forma intempestiva. Considerando o caso "
            "concreto e a possibilidade aparente de conflito desse tipo com os artigos 13, XVI (retardar "
            "ou deixar de praticar, indevidamente, ato de ofício); 14, III (deixar de cumprir ordem "
            "legal) e 14, XV (deixar de observar prazos regulamentares), do CEDM, prevalecerá o mais "
            "específico."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="VI",
        natureza="leve",
        texto="fumar em local onde esta prática seja legalmente vedada",
        comentario=(
            "O fumo prejudica não só aquele que o usa, mas também as pessoas que aspiram as substâncias "
            "tóxicas exaladas pelo cigarro. Diante disso, leis estaduais e federais proíbem a prática do "
            "tabagismo em determinados locais, prevendo multas em caso de descumprimento. É o caso da Lei "
            "Estadual n. 18.552, de 04 de dezembro de 2009, que proibiu, em Minas Gerais, a prática do "
            "tabagismo em ambientes coletivos fechados, públicos ou privados. O interior de viaturas e "
            "postos policiais e de bombeiros deve ser considerado local em que a prática do fumo é "
            "vedada. A proibição determinada na lei em destaque abrange os atos de acender, conduzir "
            "acesos e fumar cigarro, cigarrilha, charuto, cachimbo ou similares."
        ),
    ),
    Transgressao(
        artigo=15,
        inciso="VII",
        natureza="leve",
        texto="permutar serviço sem permissão da autoridade competente",
        comentario=(
            "A permuta de qualquer ato de serviço sem a devida autorização da autoridade competente "
            "redunda em desorganização e descontrole do serviço policial e de bombeiro militar. Tal "
            "permissão não carece ser escrita, desde que tempestiva e emanada pela autoridade competente "
            "para tal. Ao militar em disponibilidade cautelar é vedada a permuta de serviço, durante a "
            "vigência da medida."
        ),
    ),
]


_POR_CHAVE = {(t.artigo, t.inciso): t for t in TRANSGRESSOES}


def por_tipificacao(artigo: int, inciso: str) -> Transgressao | None:
    return _POR_CHAVE.get((artigo, inciso.strip().upper()))


def _termos(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.findall(r"[a-z0-9]+", texto)


_INDICE_BM25 = None


def _obter_indice():
    """Índice BM25 sobre texto + interpretação de cada inciso. Construído sob
    demanda (custa alguns milissegundos) e reaproveitado."""
    global _INDICE_BM25
    if _INDICE_BM25 is None:
        from rank_bm25 import BM25Okapi

        corpus = [_termos(f"{t.texto} {t.comentario}") for t in TRANSGRESSOES]
        _INDICE_BM25 = BM25Okapi(corpus)
    return _INDICE_BM25


def buscar_candidatas(descricao: str, limite: int = 8) -> list[Transgressao]:
    """Retorna as transgressões mais compatíveis com a descrição livre do
    fato, por relevância. É uma triagem lexical (BM25), não uma tipificação:
    serve para restringir o que a IA pode sugerir a um conjunto fechado de
    incisos que realmente existem no CEDM."""
    termos = _termos(descricao or "")
    if not termos:
        return []
    pontuacoes = _obter_indice().get_scores(termos)
    ordem = sorted(range(len(pontuacoes)), key=lambda i: pontuacoes[i], reverse=True)
    return [TRANSGRESSOES[i] for i in ordem[:limite] if pontuacoes[i] > 0]
