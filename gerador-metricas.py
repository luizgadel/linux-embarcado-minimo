import paho.mqtt.client as paho
import time
import psutil

def on_publish(client, userdata, mid):
    pass
 
client = paho.Client()
client.connect("18.184.101.87", 1883)
client.loop_start()

print("Publicando em tópicos")

while True:

    # Convertendo para dicionários
    mem_ram = dict(psutil.virtual_memory()._asdict())
    cpu_tempo = dict(psutil.cpu_times()._asdict())
    disco = dict(psutil.disk_usage('/')._asdict())

    #Total de memória RAM
    ram_total = str(round(mem_ram['total']/1000000000,2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/ram_total", ram_total, qos=1)

    #Total de memória RAM utilizada
    ram_utilizada = str(round(mem_ram['used']/1000000000,2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/ram_utilizada", ram_utilizada, qos=1)

    # Porcentagem de memória ram usada
    porcentagem_ram_usada = str(round(mem_ram['percent'],2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/porcentagem_ram_usada", porcentagem_ram_usada, qos=1)

    # Tempo de cpu do usuário
    cpu_usuario = str(round(cpu_tempo['user'],2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/cpu_usuario", cpu_usuario, qos=1)

    # Tempo de cpu do sistema
    cpu_sistema = str(round(cpu_tempo['system'],2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/cpu_sistema", cpu_sistema, qos=1)

    # Tempo de cpu do ocioso
    cpu_ocioso = str(round(cpu_tempo['idle'],2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/cpu_ocioso", cpu_ocioso, qos=1)

    #Total do disco
    disco_total = str(round(disco['total']/1000000000,2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/disco_total", disco_total, qos=1)

    #Total do disco usado
    disco_usado = str(round(disco['used']/1000000000,2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/disco_usado", disco_usado, qos=1)

    #Total do disco livre
    disco_livre = str(round(disco['free']/1000000000,2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/disco_livre", disco_livre, qos=1)

    client.on_publish = on_publish

    # Porcentagem de disco usado
    porcentagem_disco_usado = str(round(disco['percent'],2))
    (rc, mid) = client.publish("dse/vyctor_mikael_luiz/porcentagem_disco_usado", porcentagem_disco_usado, qos=1)
    
    time.sleep(2)
