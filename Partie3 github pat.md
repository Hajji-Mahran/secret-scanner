# Partie 3 — Token GitHub (Personal Access Token)

J'ai choisi le PAT GitHub : c'est le type de secret que j'ai planté dans mon dépôt de test, et l'un des plus critiques — il peut exposer **tout le code privé d'une organisation**.

## 1. Le reconnaître

Au préfixe :
- `ghp_` → PAT **classique**
- `github_pat_` → PAT **fine-grained**
- (`gho_` OAuth, `ghs_` app, `ghr_` refresh)

Le préfixe donne le **type**, pas les permissions : un PAT n'est **pas auto-descriptif** comme un JWT.
Regex : `ghp_[A-Za-z0-9]{36}` et `github_pat_[A-Za-z0-9_]{80,}`.

## 2. Le valider sans danger

Une seule requête, en **lecture seule**, sur le compte authentifié :

```bash
curl -i -H "Authorization: Bearer $GH_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/user
```

**Token invalide / révoqué** → `HTTP/2 401` :

```
HTTP/2 401
content-type: application/json; charset=utf-8
x-github-request-id: A1B2:1C3D:0045F6:008A1B:6720E4C0

{
  "message": "Bad credentials",
  "documentation_url": "https://docs.github.com/rest",
  "status": "401"
}
```

**Token valide** → `HTTP/2 200` + l'identité et les permissions (voir §3). Aucun effet de bord : on lit, on n'écrit rien.

## 3. Lire l'identité ET les permissions

Avec `-i`, la réponse réelle contient les **en-têtes** puis le **corps** :

```
HTTP/2 200
content-type: application/json; charset=utf-8
cache-control: private, max-age=60, s-maxage=60
x-oauth-scopes: repo, read:org, workflow
x-accepted-oauth-scopes:
x-github-media-type: github.v3; format=json
x-ratelimit-limit: 5000
x-ratelimit-remaining: 4998
x-ratelimit-reset: 1730062800
x-github-request-id: C4E2:1F3A:00912A:0122B7:6720E5D1

{
  "login": "yanis-dev",
  "id": 58323104,
  "html_url": "https://github.com/yanis-dev",
  "type": "User",
  "name": "Yanis B.",
  "company": "Acme Corp",
  "location": "Tunis",
  "email": "yanis@acme.io",
  "public_repos": 34,
  "created_at": "2015-04-10T09:12:33Z"
}
```

- **Corps** → *qui* : `login`, `name`, `company`, `email`.
- En-tête **`x-oauth-scopes`** → *permissions* : ici `repo, read:org, workflow`.

Pour n'extraire que les scopes (requête légère, en-têtes seuls) :

```bash
curl -sI -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/user | grep -i x-oauth-scopes
# -> x-oauth-scopes: repo, read:org, workflow
```

> ⚠️ **Classic vs fine-grained.** `x-oauth-scopes` n'est renseigné que pour les PAT **classiques** (`ghp_`). Pour un **fine-grained** (`github_pat_`) cet en-tête est **vide** : les permissions y sont par-dépôt, non énumérables ainsi — on ne confirme alors que l'identité via `/user`.

## 4. Pousser la reconnaissance (lecture seule, selon les scopes)

Chaque endpoint ne renvoie que ce que les scopes du token autorisent :

```
GET /user/orgs     -> organisations          (liste complète : scope read:org)
GET /user/repos    -> dépôts accessibles      (privés : scope repo)
GET /user/emails   -> adresses e-mail         (scope user:email)
```

## 5. L'impact : tout le code peut fuiter

Le scope `repo` d'un PAT **classique** n'est **pas** limité à un dépôt : il donne un accès **lecture et écriture à TOUS les dépôts privés** du compte et de ses organisations.

→ **Un seul `ghp_` fuité peut exposer l'intégralité du code source privé de l'entreprise.** Et dans ce code, l'attaquant trouve souvent d'autres secrets commités (clés cloud, mots de passe BDD) → **credential chaining** : une compromission en déclenche une autre.

## Remédiation

**Supprimer ≠ révoquer.** Retirer le token du dépôt ne le désactive pas chez GitHub — il reste valide. Il faut le **révoquer** puis le régénérer, idéalement en **fine-grained** (dépôts + permissions limités, avec expiration).
