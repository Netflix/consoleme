# Routing for Metadata Service

We highly recommend you check out the ECS credential provider emulator capability instead of using the Metadata service capability. But if needed, here are the steps:

{% tabs %}
{% tab title="Mac" %}
Run commands:

```bash
sudo ifconfig lo0 169.254.169.254 alias

echo "rdr pass on lo0 inet proto tcp from any to 169.254.169.254 port 80 -> 127.0.0.1 port 9091" | sudo pfctl -ef -
```

Alternatively to persist the settings above on a Mac, [download the plists](https://github.com/Netflix/weep/tree/master/extras) and place them in `/Library/LaunchDaemons` and reboot or issue the following commands:

```bash
launchctl load /Library/LaunchDaemons/com.user.weep.plist
launchctl load /Library/LaunchDaemons/com.user.lo0-loopback.plist
```
{% endtab %}

{% tab title="Linux" %}
Create a text file at the location of your choosing with the following contents:

```text
*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [1:216]
:POSTROUTING ACCEPT [1:216]
-A OUTPUT -d 169.254.169.254/32 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:9091
COMMIT
```

Enable the rules by running the following:

```text
sudo /sbin/iptables-restore < <path_to_file>.txt
```
{% endtab %}
{% endtabs %}

