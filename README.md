# ⚡ Byron Suite — Sécurité offensive pour API, GraphQL & serveurs MCP

> **RetroWave Edition** — Générateur de vecteurs contextuels, moteur de scan et cockpit graphique pour l'audit autorisé d'API REST/GraphQL et de serveurs MCP (Model Context Protocol).

Ce dépôt regroupe **trois outils complémentaires** qui forment une chaîne d'audit complète, de la génération de payloads jusqu'au pilotage graphique du scan :

| Outil | Rôle | Interface |
|---|---|---|
| **P-Machinery** (`P-Machivery4a.py`) | Génère des endpoints, des payloads et des *vecteurs contextuels* (association intelligente endpoint ↔ payload), avec un moteur de mutation anti-WAF | CLI |
| **Byron** (`Byron5b.py`) | Moteur de test : injections classiques, chaînes d'exploitation, mode **Mossbauer** dédié à l'audit de serveurs MCP | CLI |
| **ByronTK** (`ByronTK2b.py`) | Cockpit graphique Tkinter au look RetroWave pour piloter Byron sans ligne de commande | GUI |

```
P-Machinery  ──►  endpoints.txt + payloads/ + vectors.txt  ──►  Byron  ──►  security_test_*.log
                                                                  ▲
                                                            ByronTK (GUI)
```

---

## ⚠️ Avertissement légal

Cette suite est conçue **exclusivement pour l'audit de sécurité autorisé** : pentest sous contrat, exercices red/blue team, CTF, environnements de laboratoire vous appartenant. Elle envoie de vraies requêtes d'injection (SQLi, commande, LFI/RFI, SSRF, XXE, SSTI…) et tente activement de contourner l'authentification et les WAF. Utiliser cette suite contre un système sans autorisation écrite explicite est illégal dans la quasi-totalité des juridictions. L'auteur décline toute responsabilité en cas de mauvais usage — voir le disclaimer complet en fin de document.

---

## 📁 Structure du dépôt

```
Byroad-Sacrifice-main/
├── P-Machivery4a.py        # Générateur de wordlists offensives contextuelles + moteur anti-WAF
├── Byron5b.py               # Moteur de scan (SecurityTester, AggressionLevel, ApiType, mode Mossbauer)
├── ByronTK2b.py              # GUI Tkinter RetroWave (importe SecurityTester depuis Byron5b.py)
├── endpoints.txt             # Liste d'endpoints d'exemple (REST/GraphQL)
├── payloads.lst               # Concaténation documentée de tous les payloads par catégorie
└── payloads/                  # Un fichier par famille de vulnérabilité
    ├── sql.txt
    ├── nosql.txt
    ├── xss.txt
    ├── lfi.txt
    ├── rfi.txt
    ├── command.txt
    ├── xpath.txt
    ├── xxe.txt
    ├── xml.txt
    ├── ssrf.txt
    ├── ssti.txt
    ├── header.txt
    ├── file_upload.txt
    ├── file_download.txt
    └── caen_profonde_2075.txt   # Payloads thématiques « mémétiques » (chaîne DASHEM44)
```

> `ByronTK2b.py` importe `SecurityTester`, `AggressionLevel` et `ApiType` directement depuis `Byron5b.py` : les deux fichiers doivent rester dans le même dossier.

---

## 🚀 Installation

### Prérequis

- Python 3.8+
- `tkinter` (fourni avec la plupart des distributions Python — nécessaire uniquement pour `ByronTK2b.py`)

### Dépendances

```bash
pip install requests colorama urllib3
```

### Récupération

```bash
git clone https://github.com/doktornand/Byroad-Sacrifice.git
cd Byroad-Sacrifice-main
```

---

## 🧬 1. P-Machinery — génération de vecteurs contextuels

P-Machinery évite le produit cartésien bête (tester du SQLi sur `/actuator/health` n'a aucun sens) : chaque catégorie d'endpoint est mappée vers les familles de payloads pertinentes via `ContextMapping`.

### Catégories d'endpoints disponibles

`auth`, `users`, `admin`, `files`, `search_query`, `import_export`, `webhooks`, `graphql`, `actuator_debug`, `cloud_metadata`, `commerce`, `api_versions`, `websocket`, `mcp_ai`

### Catégories de payloads disponibles

`sql`, `nosql`, `xss`, `ssti`, `xxe`, `ssrf`, `lfi`, `command`, `ldap`, `log4j`, `graphql`, `crlf`, `redirect`, `prompt_injection`

### Mapping contextuel (extrait)

| Endpoint | Payloads associés |
|---|---|
| `auth` | sql, nosql, crlf, log4j |
| `files` | lfi, xxe, ssrf, command, ssti |
| `webhooks` | ssrf, crlf |
| `cloud_metadata` | ssrf uniquement |
| `mcp_ai` | prompt_injection, xss |
| `graphql` | graphql, sql |

### Moteur de mutation anti-WAF (`PayloadMutator`)

Quand `--mutate` est activé, chaque payload est décliné en plusieurs variantes pour contourner les WAF modernes (Cloudflare, AWS WAF, Imperva, Akamai, F5) :

- URL-encoding simple et double
- Encodage Unicode
- Entités HTML (hex / décimal)
- Casse mixte sur les mots-clés SQL (`SeLeCt`, `UnIoN`)
- Fragmentation des mots-clés SQL (commentaires inline)
- Alternatives aux espaces (`/**/`, tabulations, retours ligne)
- Variantes de null-byte
- Obfuscation de traversée de chemin (`..%2f`, double encodage, etc.)
- Pollution de paramètres JSON
- Encapsulation en base64 contextuel

### Session utilisateur type

```bash
$ python P-Machivery4a.py --list-categories

📚 CATÉGORIES DISPONIBLES (P-Machinery v4.0-CONTEXTUAL)

🏷️  ENDPOINTS (14 catégories):
  - actuator_debug        (  12 entrées)
  - admin                 (  18 entrées)
  - api_versions          (   9 entrées)
  - auth                  (  15 entrées)
  ...

💥 PAYLOADS (14 catégories):
  - command               (  22 entrées)
  - graphql               (   8 entrées)
  - log4j                 (   6 entrées)
  - sql                   (  34 entrées)
  ...

🎯 MAPPING CONTEXTUEL (ContextMapping):
  - auth                  -> sql, nosql, crlf, log4j
  - files                 -> lfi, xxe, ssrf, command, ssti
  - mcp_ai                -> prompt_injection, xss
  ...
```

**Générer un kit complet prêt à l'emploi pour Byron :**

```bash
$ python P-Machivery4a.py --byron-ready --byron-dir ./byron-kit --mutate --shuffle

================================================================================
  🏗️  CONSTRUCTION DU KIT BYRON-READY  🌌
  Dossier : ./byron-kit/
================================================================================

📡  1. Génération des Endpoints
  ----------------------------------------
  ✅ 187 endpoints générés dans ./byron-kit/endpoints.txt

💣  2. Génération des Payloads
  ----------------------------------------
  ✅ 940 payloads générés dans ./byron-kit/payloads/

🎯  3. Assemblage Contextuel des Vecteurs
  ----------------------------------------
  ✅ 1284 vecteurs contextuels générés dans ./byron-kit/vectors.txt

================================================================================
  📊 RÉSUMÉ DE LA GÉNÉRATION
================================================================================
  • Kit Byron                     : ./byron-kit/
  • Endpoints                     : 187
  • Payloads                      : 940
  • Vecteurs contextuels          : 1284
  • Mutations WAF                 : Activées
  • Mélange                       : Activé
================================================================================
```

Un `README.txt` récapitulatif (avec la commande Byron prête à copier-coller) est déposé dans `./byron-kit/`.

**Cibler une portion précise du périmètre (endpoints d'authentification uniquement) :**

```bash
$ python P-Machivery4a.py --endpoints auth,users --output-endpoints endpoints_auth.txt --shuffle
  ✅ 41 endpoints générés dans endpoints_auth.txt
```

**Générer uniquement des payloads XSS/SSRF avec mutations, en réutilisant une wordlist LFI perso :**

```bash
$ python P-Machivery4a.py --build-payloads-dir xss,ssrf --mutate \
    --lfi-file ./mes_payloads/lfi_custom.txt
  ✅ 312 payloads générés dans payloads/
```

**Vecteurs contextuels ciblés, avec plafond de sécurité :**

```bash
$ python P-Machivery4a.py --contextual-vectors files,cloud_metadata \
    --vector-file vectors_files.txt --mutate --max-vectors 500

🎯 GÉNÉRATION DE VECTEURS CONTEXTUELS
  ✅ 500 vecteurs contextuels générés dans vectors_files.txt
```

---

## 🔍 2. Byron — moteur de scan (`Byron5b.py`)

### Types d'API supportés

| Mode (`--api-type`) | Description |
|---|---|
| `rest` | Fuzzing REST classique via `endpoints.txt` (SQLi, NoSQLi, command injection, LFI/RFI, upload/download de fichiers) |
| `graphql` | Injection dans les variables GraphQL sur une requête-modèle |
| `generic` | Scan générique (SQLi, NoSQLi, command injection) sur tout endpoint HTTP |
| `mossbauer` | Scan dédié aux serveurs **MCP** — aucun fichier d'endpoints requis |

### Niveaux d'agression

| Niveau | Délai entre requêtes | Payloads utilisés par famille |
|---|---|---|
| `low` | 2.0 s | 3 premiers |
| `medium` | 1.0 s | 5 premiers |
| `high` | 0.5 s | tous |

### Options principales

| Option | Description | Défaut |
|---|---|---|
| `--target` | URL cible (requis) | — |
| `--api-type` | `rest` / `graphql` / `generic` / `mossbauer` (requis) | — |
| `--endpoints` | Fichier d'endpoints (requis hors `mossbauer`) | — |
| `--aggression` | `low` / `medium` / `high` | `medium` |
| `--taurus` | Active les tests étendus (XPath, XXE, SSRF) | désactivé |
| `--noproxy` | Scan direct sans passer par un proxy (mode furtif) | désactivé (proxy actif) |
| `--memetic-chain` | Active le **Protocole DASHEM44** (chaîne d'exploitation avancée) | désactivé |
| `--proxy-host` / `--proxy-port` | Proxy d'interception (Burp, mitmproxy…) | `192.168.1.20:8118` |
| `--auth-token` | Jeton Bearer | — |
| `--username` / `--password` | Auth basique | — |

### Session utilisateur type — scan REST via Burp Suite

```bash
$ python Byron5b.py \
    --target https://staging-api.exemple-corp.local \
    --api-type rest \
    --endpoints endpoints.txt \
    --aggression medium \
    --proxy-host 127.0.0.1 --proxy-port 8080 \
    --auth-token eyJhbGciOi...

2026-09-07 09:12:03 [INFO]
Testing endpoint: /api/v1/users/1
2026-09-07 09:12:05 [DEBUG]
==================================================
Request: GET https://staging-api.exemple-corp.local/api/v1/users/1?id=' OR '1'='1
Payload: ' OR '1'='1
Response Status: 500
Response Headers: {...}
Response Body: {"error":"SQL syntax error near ''1'='1''"}...
```
→ La réponse `500` avec message d'erreur SQL est capturée dans `security_test_20260907_091203.log` pour analyse post-scan.

### Session utilisateur type — scan direct (hors proxy) avec chaîne d'exploitation

```bash
$ python Byron5b.py \
    --target http://192.168.56.101:8000 \
    --api-type rest \
    --endpoints endpoints.txt \
    --aggression high \
    --noproxy \
    --memetic-chain

[INFO] Mode --noproxy activé : scan direct des machines en live (connexion furtive).

════════════════════════════════════════════════════════════
[MODE MEMETIC-CHAIN] Activation des tests de chaînes d'exploitation avancées (Ciblage Proteus-Lab)...
🧬 [PROTOCOLE DASHEM44] Initialisation de la chaîne d'exploitation...
🔍 [Chaîne] Extraction JWT : 200
ℹ️ [Chaîne] IDOR bloqué ou endpoint inexistant (404).
🕳️ [Injection Mémétique] Tentative de corruption sémantique...
ℹ️ [Injection Mémétique] Aucune fuite évidente détectée (ou honeypot activé).
[MODE MEMETIC-CHAIN] Tests de chaîne terminés.

Testing endpoint: /api/v1/products
...
```

`--memetic-chain` enchaîne sur les 3 premiers endpoints : tentative d'extraction de clé JWT par SQLi (`UNION SELECT kid, secret FROM jwt_keys`), forge d'un token `alg=none` pour tester un IDOR sur `/api/v1/admin/dashboard`, puis une tentative de *prompt poisoning* sur un éventuel endpoint `/mcp`.

### Session utilisateur type — audit GraphQL avec tests Taurus étendus

```bash
$ python Byron5b.py \
    --target https://api.exemple-corp.local/graphql \
    --api-type graphql \
    --endpoints endpoints.txt \
    --taurus \
    --aggression low

Testing endpoint: /graphql
2026-09-07 09:20:11 [DEBUG] Request: POST https://api.exemple-corp.local/graphql
Payload: {"input": "{\"$where\": \"return true\"}"}
Response Status: 200
```

---

## 🕵️ 3. Mode Mossbauer — audit de serveurs MCP

Le mode `mossbauer` est spécialisé pour l'audit de serveurs **Model Context Protocol** : il ne fuzz pas des endpoints REST, il parle **JSON-RPC 2.0** natif du protocole.

### Déroulé des 5 phases (`run_mossbauer`)

1. **Découverte** — sonde les chemins standards (`/mcp`, `/.well-known/mcp`, `/sse`, `/v1/mcp`…) en HTTP et en SSE jusqu'à trouver un endpoint qui répond à un `ping`.
2. **Handshake `initialize`** — envoie `protocolVersion`, `clientInfo`, `capabilities` ; affiche le nom/version du serveur et les capacités déclarées.
3. **Énumération** — liste `tools/list`, `resources/list`, `prompts/list`, `roots/list`.
4. **Injection ciblée** :
   - **4a** — sonde des méthodes JSON-RPC non documentées (`admin/executeCommand`, `internal/eval`, `debug/info`…) pour détecter des méthodes cachées accessibles.
   - **4b** — injecte command/SSTI/LFI/SQL/SSRF dans les arguments de chaque *tool* découvert, en s'appuyant sur son `inputSchema`.
   - **4c** — traverse les URI de `resources/read` (LFI type `file:///etc/passwd`, SSRF vers `169.254.169.254`).
   - **4d** — tente une **prompt injection** sur `prompts/get` (« Ignore previous instructions… », jailbreak DAN, injection SSTI dans le prompt).
5. **Bypass d'authentification** — rejoue `tools/list` avec des jeux d'en-têtes suspects (`Bearer null`, JWT `alg=none`, `X-Forwarded-For: 127.0.0.1`…) pour vérifier qu'aucun n'ouvre l'accès sans authentification légitime.

### Session utilisateur type — audit d'un serveur MCP interne

```bash
$ python Byron5b.py --target https://mcp.exemple-corp.local --api-type mossbauer --aggression medium

════════════════════════════════════════════════════════════
 MODE MOSSBAUER — MCP Security Scanner
════════════════════════════════════════════════════════════

[MOSSBAUER] Phase 1 — Découverte de l'endpoint MCP
[MOSSBAUER] ✔ Endpoint MCP trouvé (HTTP) : https://mcp.exemple-corp.local/mcp [200]

[MOSSBAUER] Phase 2 — Handshake initialize
[MOSSBAUER] Serveur : proteus-mcp-gateway v0.9.2
[MOSSBAUER] Capacités déclarées : ['tools', 'resources', 'prompts']

[MOSSBAUER] Phase 3 — Énumération (tools / resources / prompts)
[MOSSBAUER] tools (4) : search_docs, run_query, fetch_url, export_report
[MOSSBAUER] resources (2) : file:///data/reports, file:///data/cache
[MOSSBAUER] prompts : vide ou non exposé

[MOSSBAUER] Phase 4a — Sonde de méthodes JSON-RPC inconnues
[MOSSBAUER] Méthode admin/executeCommand existe (erreur -32602)

[MOSSBAUER] Phase 4b — Injection dans les outils MCP
[MOSSBAUER] → Outil : run_query (params: ['query'])
[MOSSBAUER] ⚠ Indicateur de vulnérabilité [command] sur outil 'run_query' — mots-clés : ['uid=', 'bin/bash']
 Payload : ; id; #

[MOSSBAUER] Phase 4c — Traversée de ressources (LFI/SSRF)
[MOSSBAUER] ⚠ LFI probable sur resources/read : file://../../../etc/passwd

[MOSSBAUER] Phase 4d — Prompt injection (LLM)
[MOSSBAUER] Scan terminé.
```

→ Deux constats critiques remontés immédiatement en rouge dans le log : le tool `run_query` exécute la chaîne injectée dans une commande système, et `resources/read` accepte une traversée de chemin hors du périmètre `/data/`.

---

## 🎛️ 4. ByronTK — cockpit graphique RetroWave

`ByronTK2b.py` propose une interface Tkinter complète pour piloter Byron sans terminal :

- **Onglets** Cible / Authentification / Options avancées (proxy, agression, `--taurus`, `--noproxy`, `--memetic-chain`)
- **Pill de statut** clignotante (`idle` → `scanning` → `done` / `error` / `aborted`)
- **Chronomètre** de scan en temps réel
- **Console de logs** thread-safe (ANSI strippé), avec coloration : avertissements en jaune, erreurs en rouge, événements MCP en magenta
- **Chargement/sauvegarde de configuration JSON** — pratique pour rejouer un profil de scan identique sur plusieurs cibles
- **Validation de formulaire** en direct (champ Target/Endpoints surligné en rouge si invalide ou introuvable)
- **Bouton Stop** avec confirmation (les requêtes déjà en vol ne sont pas interrompues instantanément)

### Session utilisateur type

```bash
$ python ByronTK2b.py
```

1. Onglet **Cible** : `https://staging-api.exemple-corp.local`, type d'API `rest`, fichier d'endpoints `endpoints.txt`.
2. Onglet **Authentification** : jeton Bearer collé dans le champ dédié.
3. Onglet **Options avancées** : agression `medium`, proxy `127.0.0.1:8080` pointé sur Burp, case `--taurus` cochée.
4. Clic sur **▶ Lancer le scan** → la pill passe à `scanning`, le chrono démarre, la console affiche en direct :
   ```
   [SYSTEM] ▶ Scan initialisé sur https://staging-api.exemple-corp.local (rest / medium / PROXY)
   Testing endpoint: /api/v1/users/1
   ...
   ```
5. **📂 Fichier → Sauvegarder la config** enregistre tous les champs dans `staging_profile.json`, réutilisable pour un futur scan de non-régression via **📂 Charger config JSON**.
6. En cas de scan trop long ou de cible instable, **⏹ Stop** demande confirmation puis force l'arrêt.

---

## 🔗 Chaîne d'audit complète — de zéro à l'export

```bash
# 1. Générer un kit ciblé sur l'auth et les fichiers, avec mutations anti-WAF
python P-Machivery4a.py --byron-ready --byron-dir ./kit_auth_files \
    --endpoints auth,files --payload-categories sql,nosql,lfi,ssrf,ssti --mutate

# 2. Lancer Byron sur ce kit, via proxy Burp, agression haute
python Byron5b.py \
    --target https://api.cible-autorisee.local \
    --api-type rest \
    --endpoints ./kit_auth_files/endpoints.txt \
    --aggression high \
    --proxy-host 127.0.0.1 --proxy-port 8080

# 3. Reprendre le pilotage en GUI pour un second passage avec --taurus et --memetic-chain
python ByronTK2b.py
```

---

## ⚙️ Notes de développement

- `ByronTK2b.py` applique un patch de compatibilité : si `get_request_delay` / `get_payload_count` manquent sur `AggressionLevel` dans `Byron5b.py`, la GUI les recrée dynamiquement.
- Les logs sont doublement écrits : sur `stdout` (console CLI ou console GUI) et dans un fichier `security_test_<horodatage>.log` détaillé (requête, payload, statut, en-têtes, 1000 premiers caractères du corps de réponse).
- Le module `PayloadMutator` de P-Machinery est autonome et peut être réutilisé indépendamment du reste de la suite pour muter n'importe quelle liste de payloads.
- Les fichiers `payloads/*.txt` sont rechargés à chaque lancement de Byron : les personnaliser directement (ou les régénérer via P-Machinery) est le moyen le plus simple d'adapter la couverture de test à un contexte métier précis.

---

## 📄 Licence

Ce projet ne spécifie pas de licence à ce jour. Contactez l'auteur avant toute redistribution ou modification.

---

## ⚠️ Disclaimer complet

Byron Suite (P-Machinery, Byron, ByronTK) est fournie à des fins **d'audit de sécurité autorisé uniquement** : tests d'intrusion sous mandat écrit, exercices red/blue team encadrés, environnements de laboratoire dont vous êtes propriétaire, CTF. L'utilisation de cet outil contre un système, une API ou un serveur MCP sans autorisation explicite et écrite du propriétaire est illégale dans la plupart des juridictions et peut engager votre responsabilité civile et pénale. L'auteur n'assume aucune responsabilité pour tout usage détourné, non autorisé ou dommageable de cette suite.

*Made with 💜 and neon lights by [doktornand](https://github.com/doktornand)*
