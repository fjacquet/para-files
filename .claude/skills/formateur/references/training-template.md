# Templates de Formation - Référence

Ce fichier contient les templates détaillés extraits des formations existantes pour servir de modèle.

---

## 1. Template Roadmap Complet

```markdown
---
created: "{{DATE}}T10:00"
updated: "{{DATE}}T10:00"
tags:
  - topic/formation
  - topic/roadmap
  - topic/{{SUJET_LOWERCASE}}
  - status/permanent
aliases:
  - {{SUJET}} Training Roadmap
  - Formation {{SUJET}}
  - {{SUJET}} Ninja Path
type: roadmap
---

# Formation {{SUJET}} : De Débutant à {{SUJET}} Ninja

## Overview

Ce parcours de formation structuré vous guide de zéro à expert {{SUJET}}. Basé sur {{STACK_TECHNIQUE}}, il couvre tous les aspects : des concepts fondamentaux jusqu'à la production et le troubleshooting avancé.

## Progression Pédagogique

```
DÉBUTANT ──────► JUNIOR ──────► CONFIRMÉ ──────► SENIOR ──────► {{SUJET}} NINJA
    │              │               │               │               │
    ▼              ▼               ▼               ▼               ▼
 Module 0      Module 1        Modules 2-3     Modules 4-6      Module 7
 Prérequis    Fondamentaux    Architecture    {{DOMAINE_1}}    Production
                              {{DOMAINE_2}}   {{DOMAINE_3}}    Expertise
```

## Graphe des Dépendances

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    {{SUJET}} NINJA PATH                      │
                    └─────────────────────────────────────────────────────────────┘

┌──────────────┐
│   Module 0   │
│  Prérequis   │
│  {{PREREQ}} │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Module 1   │
│ Fondamentaux │──────────────────────────────────────────────────┐
│   {{SUJET}} │                                                   │
└──────┬───────┘                                                   │
       │                                                           │
       ▼                                                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Module 2   │───►│   Module 3   │───►│   Module 4   │    │   Module 5   │
│ {{TOPIC_2}} │    │ {{TOPIC_3}} │    │ {{TOPIC_4}} │    │ {{TOPIC_5}} │
│              │    │              │    │              │    │              │
└──────────────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
                           │                   │                   │
                           ▼                   │                   │
                    ┌──────────────┐           │                   │
                    │   Module 6   │◄──────────┴───────────────────┘
                    │ {{TOPIC_6}} │
                    │              │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Module 7   │
                    │  Production  │
                    │  Expertise   │
                    └──────────────┘
```

## Modules de Formation

### Module 0 : Prérequis et Environnement

| Status | Fiche | Sujet | Prérequis |
|--------|-------|-------|-----------|
| - [ ] | [[{{DATE}}-00-prerequis-{{SUJET_LOWERCASE}}]] | Auto-évaluation, installation | Aucun |

### Module 1 : Fondamentaux {{SUJET}}

| Status | Fiche | Sujet | Prérequis |
|--------|-------|-------|-----------|
| - [ ] | [[{{DATE}}-01-{{SUJET_LOWERCASE}}-concepts]] | Concepts de base | Module 0 |
| - [ ] | [[{{DATE}}-02-{{SUJET_LOWERCASE}}-installation]] | Installation et configuration | Module 0 |
| - [ ] | [[{{DATE}}-03-{{SUJET_LOWERCASE}}-cli]] | Outils en ligne de commande | 01, 02 |

### Module 2 : {{DOMAINE_1}}

| Status | Fiche | Sujet | Prérequis |
|--------|-------|-------|-----------|
| - [ ] | [[{{DATE}}-04-...]] | ... | Module 1 |
| - [ ] | [[{{DATE}}-05-...]] | ... | 04 |

[... autres modules ...]

## Stack Technique

| Composant | Technologie |
|-----------|-------------|
| **Runtime** | {{RUNTIME}} |
| **Orchestration** | {{ORCH}} |
| **Langage** | {{LANGAGE}} |
| **IDE** | VS Code + extensions |

## Temps Estimé par Module

| Module | Durée | Cumul |
|--------|-------|-------|
| 0 - Prérequis | 2-3h | 3h |
| 1 - Fondamentaux | 6-8h | 11h |
| 2 - {{DOMAINE_1}} | 6-8h | 19h |
| 3 - {{DOMAINE_2}} | 8-10h | 29h |
| 4 - {{DOMAINE_3}} | 6-8h | 37h |
| 5 - {{DOMAINE_4}} | 6-8h | 45h |
| 6 - Sécurité | 6-8h | 53h |
| 7 - Production | 8-10h | 63h |

**Durée totale estimée : 50-70 heures**

## Ressources Complémentaires

### Documentation Officielle
- [{{SUJET}} Documentation]({{URL_DOC}})

### Livres Recommandés
- "{{LIVRE_1}}" ({{EDITEUR}})

### Glossaire
- [[{{SUJET_LOWERCASE}}]] - {{SUJET}} définition

## Next Actions

- [ ] #next Commencer par [[{{DATE}}-00-prerequis-{{SUJET_LOWERCASE}}]]
- [ ] #next Configurer l'environnement de développement
```

---

## 2. Template Module Standard

```markdown
---
created: "{{DATE}}T10:00"
updated: "{{DATE}}T10:00"
tags:
  - howto
  - topic/{{SUJET_LOWERCASE}}
  - status/permanent
aliases:
  - {{TITRE_COURT}}
type: howto
module: {{N}}
---

# {{TITRE_MODULE}}

## Overview

{{DESCRIPTION_MODULE}} Ce module couvre les concepts essentiels : {{LISTE_CONCEPTS}}.

## Prerequisites

- [ ] [[{{DATE}}-{{N-1}}-...]] complété
- [ ] {{PREREQUIS_TECHNIQUE}}

## {{CONCEPT_1}}

### Définition

{{EXPLICATION_CONCEPT}}

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           {{TITRE_DIAGRAMME}}                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Block 1    │  │   Block 2    │  │   Block 3    │                  │
│  │              │  │              │  │              │                  │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │                  │
│  │ │ Sub 1    │ │  │ │ Sub 2    │ │  │ │ Sub 3    │ │                  │
│  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Exemple de Code

```{{LANGAGE}}
# {{COMMENTAIRE}}
{{CODE_EXEMPLE}}
```

## {{CONCEPT_2}}

### Explication

{{CONTENU}}

| Propriété | Description |
|-----------|-------------|
| {{PROP_1}} | {{DESC_1}} |
| {{PROP_2}} | {{DESC_2}} |

## {{CONCEPT_3}}

### {{SOUS_SECTION}}

```
Diagramme de flux:

Component A                  Component B                 Component C
   │                          │                          │
   │  1. Action(data)         │                          │
   │ ─────────────────────────►                          │
   │                          │                          │
   │  2. Process data         │                          │
   │                          │                          │
   │  3. Response(result)     │                          │
   │ ◄─────────────────────────                          │
   │                          │                          │
   │                          │  4. Forward(result)      │
   │                          │ ─────────────────────────►
```

## Exercices Pratiques

### Exercice 1 : {{NOM_EXERCICE_1}} (Facile)

**Objectif** : {{OBJECTIF_EXERCICE_1}}

**Contexte** : {{CONTEXTE_EXERCICE_1}}

**Instructions** :
1. {{ETAPE_1}}
2. {{ETAPE_2}}
3. {{ETAPE_3}}

**Résultat attendu** : {{RESULTAT_ATTENDU_1}}

**Indice** : {{INDICE_1}}

---

### Exercice 2 : {{NOM_EXERCICE_2}} (Moyen)

**Objectif** : {{OBJECTIF_EXERCICE_2}}

**Contexte** : {{CONTEXTE_EXERCICE_2}}

**Instructions** :
1. {{ETAPE_1}}
2. {{ETAPE_2}}
3. {{ETAPE_3}}
4. {{ETAPE_4}}

**Résultat attendu** : {{RESULTAT_ATTENDU_2}}

**Bonus** : {{BONUS_2}}

---

### Exercice 3 : {{NOM_EXERCICE_3}} (Difficile)

**Objectif** : {{OBJECTIF_EXERCICE_3}}

**Contexte** : {{CONTEXTE_EXERCICE_3}}

**Instructions** :
1. {{ETAPE_1}}
2. {{ETAPE_2}}
3. {{ETAPE_3}}
4. {{ETAPE_4}}
5. {{ETAPE_5}}

**Critères de réussite** :
- [ ] {{CRITERE_1}}
- [ ] {{CRITERE_2}}
- [ ] {{CRITERE_3}}

**Résultat attendu** : {{RESULTAT_ATTENDU_3}}

## Tips and Best Practices

- **{{CONSEIL_1}}** : {{EXPLICATION_1}}
- **{{CONSEIL_2}}** : {{EXPLICATION_2}}
- **{{CONSEIL_3}}** : {{EXPLICATION_3}}
- **{{CONSEIL_4}}** : {{EXPLICATION_4}}

## Limitations or Common Issues

| Problème | Cause | Solution |
|----------|-------|----------|
| {{PROBLEME_1}} | {{CAUSE_1}} | {{SOLUTION_1}} |
| {{PROBLEME_2}} | {{CAUSE_2}} | {{SOLUTION_2}} |
| {{PROBLEME_3}} | {{CAUSE_3}} | {{SOLUTION_3}} |

## Related Concepts

- [[{{CONCEPT_RELATED_1}}]] - {{DESCRIPTION_1}}
- [[{{CONCEPT_RELATED_2}}]] - {{DESCRIPTION_2}}
- [[{{DATE}}-{{N+1}}-...]] - Module suivant

## Next Actions

- [ ] #next Faire les 3 exercices de ce module
- [ ] #next Réviser les concepts clés
- [ ] #next Passer à [[{{DATE}}-{{N+1}}-...]]
```

---

## 3. Template Module Prérequis (Module 0)

```markdown
---
created: "{{DATE}}T10:00"
updated: "{{DATE}}T10:00"
tags:
  - howto
  - topic/{{SUJET_LOWERCASE}}
  - status/permanent
aliases:
  - {{SUJET}} Prerequisites
  - Prérequis {{SUJET}}
type: howto
module: 0
---

# Prérequis et Environnement {{SUJET}}

## Overview

Avant de commencer la formation {{SUJET}}, assurez-vous de maîtriser les concepts fondamentaux et d'avoir configuré votre environnement de développement.

## Auto-Évaluation des Prérequis

### Compétences Requises

| Compétence | Niveau requis | Auto-évaluation |
|------------|---------------|-----------------|
| {{COMPETENCE_1}} | Basique | ☐ Maîtrisé ☐ À revoir |
| {{COMPETENCE_2}} | Basique | ☐ Maîtrisé ☐ À revoir |
| {{COMPETENCE_3}} | Intermédiaire | ☐ Maîtrisé ☐ À revoir |
| {{COMPETENCE_4}} | Basique | ☐ Maîtrisé ☐ À revoir |

### Questions de Vérification

1. **{{QUESTION_1}}**
   - Réponse attendue : {{REPONSE_1}}

2. **{{QUESTION_2}}**
   - Réponse attendue : {{REPONSE_2}}

3. **{{QUESTION_3}}**
   - Réponse attendue : {{REPONSE_3}}

> **Score** : Si vous avez répondu correctement à 2/3 questions, vous pouvez continuer.
> Sinon, révisez les ressources ci-dessous.

## Installation de l'Environnement

### 1. {{OUTIL_1}}

```bash
# Installation
{{COMMANDE_INSTALL_1}}

# Vérification
{{COMMANDE_CHECK_1}}
```

### 2. {{OUTIL_2}}

```bash
# Installation
{{COMMANDE_INSTALL_2}}

# Vérification
{{COMMANDE_CHECK_2}}
```

### 3. {{OUTIL_3}}

```bash
# Installation
{{COMMANDE_INSTALL_3}}

# Vérification
{{COMMANDE_CHECK_3}}
```

## Configuration de l'IDE

### VS Code Extensions

| Extension | Description |
|-----------|-------------|
| {{EXTENSION_1}} | {{DESC_EXT_1}} |
| {{EXTENSION_2}} | {{DESC_EXT_2}} |
| {{EXTENSION_3}} | {{DESC_EXT_3}} |

### Configuration Recommandée

```json
{
  "{{SETTING_1}}": {{VALUE_1}},
  "{{SETTING_2}}": {{VALUE_2}}
}
```

## Ressources de Mise à Niveau

Si vous avez besoin de réviser certains prérequis :

| Compétence | Ressource recommandée |
|------------|----------------------|
| {{COMPETENCE_1}} | [{{RESSOURCE_1}}]({{URL_1}}) |
| {{COMPETENCE_2}} | [{{RESSOURCE_2}}]({{URL_2}}) |
| {{COMPETENCE_3}} | [{{RESSOURCE_3}}]({{URL_3}}) |

## Vérification Finale

Avant de passer au Module 1, assurez-vous que :

- [ ] Toutes les installations sont vérifiées
- [ ] L'IDE est configuré
- [ ] Vous pouvez exécuter les commandes de base
- [ ] Vous avez créé un dossier de travail pour les exercices

## Next Actions

- [ ] #next Compléter l'auto-évaluation
- [ ] #next Installer l'environnement
- [ ] #next Passer à [[{{DATE}}-01-{{SUJET_LOWERCASE}}-concepts]]
```

---

## 4. Diagrammes ASCII Réutilisables

### Architecture Client-Server

```
┌───────────────┐           ┌───────────────┐
│    CLIENT     │           │    SERVER     │
│               │           │               │
│ ┌───────────┐ │  Request  │ ┌───────────┐ │
│ │  App UI   │ │ ─────────►│ │   API     │ │
│ └───────────┘ │           │ └───────────┘ │
│               │  Response │               │
│               │ ◄─────────│               │
└───────────────┘           └───────────────┘
```

### Architecture Microservices

```
                    ┌──────────────────────────────────────┐
                    │            API GATEWAY               │
                    └──────────────┬───────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service A     │    │   Service B     │    │   Service C     │
│   ┌─────────┐   │    │   ┌─────────┐   │    │   ┌─────────┐   │
│   │   DB    │   │    │   │   DB    │   │    │   │   DB    │   │
│   └─────────┘   │    │   └─────────┘   │    │   └─────────┘   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Pipeline de données

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ SOURCE  │───►│ INGEST  │───►│TRANSFORM│───►│  STORE  │───►│  SERVE  │
│         │    │         │    │         │    │         │    │         │
│ • APIs  │    │ • ETL   │    │ • Clean │    │ • DW    │    │ • BI    │
│ • Files │    │ • Stream│    │ • Enrich│    │ • Lake  │    │ • API   │
│ • DBs   │    │ • Batch │    │ • Agg   │    │ • OLAP  │    │ • ML    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Flux de messages

```
Producer                    Broker                     Consumer
   │                          │                          │
   │  1. Send(message)        │                          │
   │ ─────────────────────────►                          │
   │                          │                          │
   │  2. Acknowledge          │                          │
   │ ◄─────────────────────────                          │
   │                          │                          │
   │                          │  3. Poll()               │
   │                          │ ◄─────────────────────────
   │                          │                          │
   │                          │  4. Deliver(message)     │
   │                          │ ─────────────────────────►
   │                          │                          │
   │                          │  5. Commit               │
   │                          │ ◄─────────────────────────
```

### Arbre de décision

```
                        ┌──────────────┐
                        │   Décision   │
                        │   initiale   │
                        └──────┬───────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
       ┌─────────────┐                   ┌─────────────┐
       │  Option A   │                   │  Option B   │
       └──────┬──────┘                   └──────┬──────┘
              │                                 │
         ┌────┴────┐                       ┌────┴────┐
         ▼         ▼                       ▼         ▼
    ┌────────┐ ┌────────┐             ┌────────┐ ┌────────┐
    │ A.1    │ │ A.2    │             │ B.1    │ │ B.2    │
    └────────┘ └────────┘             └────────┘ └────────┘
```

---

## 5. Prompts nano-banana par Domaine

### DevOps / Infrastructure

```
Professional training course banner for DevOps and Infrastructure.
Modern flat design with geometric server racks, CI/CD pipelines, containers.
Blue and gray color palette with orange accents.
Icons: servers, pipelines, clouds, gears.
Tech education aesthetic, clean and professional.
```

### Data Engineering

```
Professional training course banner for Data Engineering.
Modern flat design with data flows, pipelines, databases.
Purple and orange color palette with white accents.
Icons: data streams, SQL tables, ETL arrows, charts.
Tech education aesthetic, analytical feel.
```

### Cloud Computing

```
Professional training course banner for Cloud Computing.
Modern flat design with cloud icons, network connections.
Sky blue and white color palette with gray accents.
Icons: clouds, servers, global network, scaling arrows.
Tech education aesthetic, expansive feel.
```

### Security

```
Professional training course banner for Cybersecurity.
Modern flat design with shields, locks, firewalls.
Dark red and black color palette with white accents.
Icons: shields, padlocks, keys, warning signs.
Tech education aesthetic, protective feel.
```

### Programming / Development

```
Professional training course banner for Software Development.
Modern flat design with code brackets, terminal windows.
Green and dark gray color palette with white accents.
Icons: code blocks, git branches, terminal, IDE windows.
Tech education aesthetic, creative feel.
```
