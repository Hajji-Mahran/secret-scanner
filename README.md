# Secret Scanner

Scanner de secrets **récupérables** dans un dépôt Git local. Lecture seule, 100 % local, aucun appel réseau.

```bash
python scan.py /chemin/vers/un/repo [--pretty] [--redact]
```

---

## Ce que le scanner fait

**Entrée** — un chemin de dépôt Git quelconque. Il vérifie que c'en est un et ne présume rien de sa structure.

**Collecte (2 sources complémentaires)**
- **Working tree** : tous les fichiers du disque, y compris non suivis / ignorés (texte).
- **Objets Git** : tous les blobs via `git cat-file --batch-all-objects` — atteignables **et** orphelins, loose **et** packés.

**Normalisation**
- Déduplication par hash de contenu.
- Fichiers binaires écartés.
- Décodage des blocs **base64** probables, puis re-scan.

**Détection (moteur en couches)**
- Motifs par fournisseur : AWS, GitHub, Slack, Hugging Face, OpenAI, clé privée PEM, **JWT**.
- En-têtes `Authorization: Basic/Bearer`.
- Motifs génériques (mots-clés `password`, `secret`, `api_key`).
- **Entropie de Shannon** (secrets de format inconnu).
- Chaque trouvaille porte un `confidence` (high/medium/low) et un flag `needs_review`.

**Enrichissement** — pour chaque secret : `type`, `path`, `commit`, `author`, `date` (`null` si le blob n'est dans aucun commit, ex. stagé).

**Sortie** — JSON parsable par machine (`--pretty` pour l'indenter, `--redact` pour masquer la valeur).

**Techniques de dissimulation couvertes** : fichier supprimé, `amend` (reflog), `rebase` (orphelin), branche supprimée (orphelin), stash droppé (dangling), stash vivant, blob stagé jamais commité, encodage base64.

---

## Ce que le scanner ne fait pas

**Angles morts (internes Git non scannés)**
- **Binaires / UTF-16** : fichiers avec octets nuls → écartés (un secret caché dedans est raté).
- Messages de commit, messages de tags annotés, noms de branches / tags.
- `.git/config` (URLs de remote avec identifiants), `.git/hooks/`.
- Submodules (dépôts imbriqués, leur propre base d'objets).

**Limites de détection (intrinsèques)**
- **Binaires / UTF-16** : fichiers avec octets nuls → écartés (un secret caché dedans est raté).
- Secrets **chiffrés** : illisibles sans la clé → non détectés.
- Secrets **fragmentés** (`"a" + "b"`) : pas fiable en analyse statique.
- Contenu **binaire / UTF-16** : écarté (octet nul).
- Base64 **imbriqué** : une seule couche décodée.

**Faux positifs** — l'entropie signale aussi des hash, UUID, JS minifié. Ils sont **tagués `needs_review`**, jamais présentés comme un verdict.

**Hors scope (poste développeur, pas le dépôt)** — historiques shell, `~/.aws`, variables d'environnement, logs, couches Docker, dumps mémoire. Exclus **volontairement** : l'outil scanne un *dépôt Git*, pas une machine.

---

## Sécurité

Le scanner **lit, signale, et s'arrête là**. Il ne se sert jamais des secrets trouvés et ne les envoie nulle part. La validation **live** (réseau) est hors périmètre par défaut — opt-in uniquement.

---

## Architecture

```
scan.py              point d'entrée (CLI + orchestration)
scanner/
  collect.py         working tree + tous les objets Git 
  detect.py          moteur de détection (motifs, base64, entropie)
  enrich.py          blob -> chemin / commit / auteur / date
  report.py          sortie JSON
```

Chaque module a une responsabilité unique et communique par des dicts simples → testable isolément, extensible sans toucher au cœur.