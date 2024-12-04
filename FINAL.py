"""
OBS para rodar o código as bibliotecas cv2 e mediapipe devem ser instaladas, preferencialmente com a mesma versão do código
mediapipe: 0.10.18
opencv-python: 4.10.0.84
"""
import cv2
import mediapipe as mp
import time
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Inicializa a captura da webcam e configurações do MediaPipe
try:
    captura = cv2.VideoCapture(0)
    if not captura.isOpened():
        raise Exception("Erro ao acessar a webcam.")
except Exception as e:
    print(f"Erro na captura da webcam: {e}")
    exit()

mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

# Configuração de controle de volume
try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volRange = volume.GetVolumeRange()
    minVol = volRange[0]
    maxVol = volRange[1]
except Exception as e:
    print(f"Erro ao acessar o controle de volume: {e}")
    exit()

passadoTime = 0
atualTime = 0

# IDs dos pontos que representam as pontas dos dedos (polegar, indicador, médio, anelar, mínimo)
dedo_ids = [4, 8, 12, 16, 20]
thumb_id = 4  # ID do polegar

# Variáveis de estado do menu e função ativa
menu_ativo = True
funcao_ativa = None
temporizador_inicial = 0  # Tempo inicial para contagem de segundos
tempo_esperado = 5  # Tempo necessário para manter o sinal em segundos
numero_dedos_ativo = None  # Armazena o número de dedos levantados

# Variáveis de confirmação de sinal
sinal_atual = None
temporizador_sinal = 0
em_confirmacao = False  # Indica se está em processo de confirmação ou cancelamento

# Controle de mensagens temporárias
mensagem_atual = None
tempo_mensagem = 0
duracao_mensagem = 3  # Tempo de exibição da mensagem (em segundos)

def exibir_mensagem(img, posicao=(10, 400), tamanho=2, cor=(0, 255, 0), espessura=2):
    #Exibe uma mensagem temporária na tela.

    global mensagem_atual, tempo_mensagem
    if mensagem_atual and time.time() - tempo_mensagem <= duracao_mensagem:
        cv2.putText(img, mensagem_atual, posicao, cv2.FONT_HERSHEY_PLAIN, tamanho, cor, espessura)
    elif mensagem_atual:
        mensagem_atual = None

def ativar_mensagem(texto):
    #Ativa uma mensagem temporária.

    global mensagem_atual, tempo_mensagem
    mensagem_atual = texto
    tempo_mensagem = time.time()

def calcular_distancia(ponto1, ponto2):
    return math.hypot(ponto2[0] - ponto1[0], ponto2[1] - ponto1[1])

def obter_posicao_dedos(hand_landmarks, img):
    h, w, _ = img.shape
    pontos = {}
    for id, lm in enumerate(hand_landmarks.landmark):
        cx, cy = int(lm.x * w), int(lm.y * h)
        pontos[id] = (cx, cy)
    return pontos

def dedos_levantados(hand_landmarks):
    """Detecta quais dedos estão levantados."""
    dedos_levantados = []
    for i, id in enumerate(dedo_ids):
        if i == 0:  # Para o polegar (checa eixo x)
            if hand_landmarks.landmark[id].x < hand_landmarks.landmark[id - 2].x:
                dedos_levantados.append(1)
            else:
                dedos_levantados.append(0)
        else:  # Para os outros dedos (checa eixo y)
            if hand_landmarks.landmark[id].y < hand_landmarks.landmark[id - 2].y:
                dedos_levantados.append(1)
            else:
                dedos_levantados.append(0)
    return dedos_levantados

def detectar_sinal(hand_landmarks):
    #Detecta sinal de positivo (polegar para cima) ou negativo (polegar para baixo).

    thumb_tip = hand_landmarks.landmark[thumb_id]
    thumb_base = hand_landmarks.landmark[thumb_id-1]
    if thumb_tip.y < thumb_base.y:
        return "positivo"
    elif thumb_tip.y > thumb_base.y:
        return "negativo"
    return None

def funcao2():
    ativar_mensagem("Funcao 2 ativa - Outra Acao")

def ControleVolume(hand_landmarks, img):
    #Ajusta o volume do sistema com base na quantidade de dedos levantados.

    global volume, minVol, maxVol

    tempo_inicio = None  # Para controlar os 5 segundos
    numero_dedos_anteriores = None  # Para verificar mudanças no número de dedos

    while True:
        try:
            # Captura o frame e processa landmarks novamente
            success, frame = captura.read()
            if not success:
                raise Exception("Falha ao capturar o frame da câmera.")

            imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(imgRGB)

            if results.multi_hand_landmarks:
                for handLms in results.multi_hand_landmarks:
                    # Obtém os dedos levantados
                    dedos = dedos_levantados(handLms)
                    numero_dedos = sum(dedos)

                    # Inicia ou reinicia o temporizador se o número de dedos mudar
                    if numero_dedos != numero_dedos_anteriores:
                        numero_dedos_anteriores = numero_dedos
                        tempo_inicio = time.time()  # Reinicia o temporizador

                    # Calcula o tempo decorrido
                    tempo_decorrido = time.time() - tempo_inicio if tempo_inicio else 0

                    # Exibe o temporizador na tela
                    if tempo_inicio:
                        cv2.putText(frame, f"Aguardando... {int(tempo_decorrido)}s", (10, 150), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 0), 2)

                    # Verifica se 5 segundos se passaram
                    if tempo_inicio and tempo_decorrido >= 5:
                        # Ajusta o volume com base no número de dedos
                        if numero_dedos == 1:
                            novo_volume = 0
                            mensagem_volume = "Volume: 0%"
                        elif numero_dedos == 2:
                            novo_volume = 0.25
                            mensagem_volume = "Volume: 25%"
                        elif numero_dedos == 3:
                            novo_volume = 0.50
                            mensagem_volume = "Volume: 50%"
                        elif numero_dedos == 4:
                            novo_volume = 0.75
                            mensagem_volume = "Volume: 75%"
                        elif numero_dedos == 5:
                            novo_volume = 1.0
                            mensagem_volume = "Volume: 100%"
                        else:
                            mensagem_volume = "Nenhuma ação de volume"
                            continue

                        # Define o volume do sistema
                        volume.SetMasterVolumeLevelScalar(novo_volume, None)


                        # Exibe a mensagem do volume
                        cv2.putText(frame, mensagem_volume, (10, 100), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

                        # Após ajustar o volume, fecha a janela automaticamente
                        cv2.imshow("Controle de Volume", frame)
                        print(mensagem_volume)  # Feedback no console
                        time.sleep(2)  # Pequeno atraso antes de fechar
                        cv2.destroyWindow("Controle de Volume")
                        return  # Sai da função após ajustar o volume

                    # Exibe landmarks na mão
                    mpDraw.draw_landmarks(frame, handLms, mpHands.HAND_CONNECTIONS)

            # Mostra o frame na janela
            cv2.imshow("Controle de Volume", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break  # Sai do controle de volume ao pressionar 'q'

        except Exception as e:
            print(f"Erro no controle de volume: {e}")
            break  # Sai do loop caso haja erro

    cv2.destroyWindow("Controle de Volume")  # Fecha a janela ao encerrar o loop

while True:
    try:
        success, img = captura.read()
        if not success:
            raise Exception("Falha ao capturar o frame da câmera.")
        
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                pontos = obter_posicao_dedos(handLms, img)
                dedos = dedos_levantados(handLms)
                numero_dedos = sum(dedos)

                if menu_ativo and not em_confirmacao:
                    if numero_dedos == numero_dedos_ativo:
                        tempo_passado = time.time() - temporizador_inicial
                        cv2.putText(img, f"Aguardando... {int(tempo_passado)}s", (10, 150), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 0), 2)

                        if tempo_passado >= tempo_esperado:
                            if numero_dedos == 1:
                                funcao_ativa = 1
                                em_confirmacao = True
                                ativar_mensagem("Opcao 1 selecionada")
                            elif numero_dedos == 2:
                                funcao_ativa = 2
                                em_confirmacao = True
                                ativar_mensagem("Opcao 2 selecionada")
                    else:
                        temporizador_inicial = time.time()
                        numero_dedos_ativo = numero_dedos

                if em_confirmacao:
                    sinal = detectar_sinal(handLms)

                    if sinal == sinal_atual and sinal is not None:
                        tempo_sinal = time.time() - temporizador_sinal
                        cv2.putText(img, f"Confirmando... {int(tempo_sinal)}s", (10, 300), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 0), 2)

                        if tempo_sinal >= tempo_esperado:
                            if sinal == "positivo":
                                ativar_mensagem("Confirmado")
                                menu_ativo = False
                                em_confirmacao = False
                            elif sinal == "negativo":
                                ativar_mensagem("Cancelado")
                                funcao_ativa = None
                                em_confirmacao = False
                                menu_ativo = True
                                numero_dedos_ativo = None
                                temporizador_inicial = time.time()
                                sinal_atual = None
                    else:
                        temporizador_sinal = time.time()
                        sinal_atual = sinal

                mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)

        if not menu_ativo:
            if funcao_ativa == 1:
                ControleVolume(handLms, img)
                # Redefine o estado para voltar ao menu
                menu_ativo = True
                funcao_ativa = None
                numero_dedos_ativo = None
                temporizador_inicial = time.time()

        exibir_mensagem(img)

        atualTime = time.time()
        fps = 1 / (atualTime - passadoTime)
        passadoTime = atualTime
        cv2.putText(img, f'FPS: {int(fps)}', (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 0), 3)

        cv2.imshow("Menu Principal", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    except Exception as e:
        print(f"Erro no loop principal: {e}")
        break  # Sai do loop caso haja erro

captura.release()
cv2.destroyAllWindows()
