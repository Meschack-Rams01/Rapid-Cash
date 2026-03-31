# 📘 Manuel d'Utilisation - Rapid Cash (Manager)

Bienvenue dans le manuel d'utilisation officiel de **Rapid Cash**. Ce système a été conçu pour offrir une gestion de caisse fluide, sécurisée et intelligente, adaptée à une structure multi-agents et multi-devises.

---

## 👥 1. Les Rôles Utilisateurs

Le système fonctionne avec deux niveaux d'accès stricts :

### A. L'Agent (Opérateur)
C'est l'employé sur le terrain. Il n'a accès qu'au strict minimum pour éviter les erreurs ou les fuites de données financières.
- **Ce qu'il peut faire :**
  - Enregistrer de nouvelles opérations (Dépôts, Retraits, Transferts).
  - Consulter l'historique de **ses propres** opérations.
  - Voir son tableau de bord personnel (statistiques de la journée).
- **Règle vitale :** Un agent opère de manière indépendante. Le système enregistre tout sans jamais le "bloquer", même si sa caisse virtuelle semble insuffisante. L'argent physique et le système numérique sont gérés en "confiance modérée" (Auditable plus tard par l'Admin).

### B. L'Administrateur (Vous)
C'est le chef d'orchestre. Il a accès à **tout**. Il supervise l'argent physique, les bénéfices, la paie, et le capital.

---

## 💶 2. Menu : Opérations & Trésorerie
*Concerne les flux d'argent quotidiens.*

- **Nouvelle Opération :** Permet (aux agents ou à vous) d'enregistrer une transaction client (ex: un client vient retirer ou déposer de l'argent). Les commissions sont automatiquement calculées.
- **Historique :** Le livre de compte de toutes les transactions passées.
- **Trésorerie > Caisses Virtuelles :** Affiche le solde théorique de chaque agent. Si un agent fait un Dépôt, sa caisse monte. S'il fait un Retrait (donne de l'argent au client), sa caisse descend.
- **Trésorerie > Allocations Agents :** C'est ici que l'Admin enregistre chaque fois qu'il remet de l'argent liquide (ou un solde Mobile Money) à un Agent pour qu'il puisse travailler. Cela augmente la Caisse de l'agent de manière tracée.

---

## 🏦 3. Menu : Finance & Capital
*Concerne l'argent de l'entreprise (pas celui des clients).*

- **Finance > Mouvements Capital :** À utiliser **uniquement** lorsque vous (ou les investisseurs) injectez de l'argent de votre poche pour faire grandir le business, ou retirez une partie de ce capital de départ.
- **Finance > Dépenses :** Permet d'enregistrer les frais de fonctionnement de l'agence (Carburant, Internet, Loyer, Électricité). Ces dépenses sont soustraites directement des revenus totaux à la fin du mois.
- **Finance > Retraits Bénéfices :** Contrairement au "Capital", ici vous enregistrez l'argent que vous prenez dans les **gains** (les commissions) pour vous payer ou payer les dividendes des investisseurs. **Cet écran justifie où est passé l'argent gagné.**
- **Finance > Commissions :** Un rapport listant toutes les taxes et frais récoltés sur chaque opération client. C'est le revenu brut du business.

---

## 🗓️ 4. Menu : Paie & Équipe
*Gère la clôture mensuelle et le partage de la richesse.*

- **Gestion de la Paie (Tableau de Bord) :** C'est le cœur financier. En un clin d'œil, il calcule pour le mois en cours :
  1. **Revenus (Total des frais)** : L'argent gagné par les commissions.
  2. **Dépenses** : Ce que l'agence a dépensé pour tourner.
  3. **Montant Réservé (%)** : L'argent mis de côté pour grossir le fond de roulement (la réserve).
  4. **Bénéfice Net à Distribuer** : L'argent restant qui peut être payé aux employés/associés.
- C'est aussi ici que vous calculez d'un clic les fiches de paie de la période et que vous les marquez comme "Payées".
- **Agents, Associés, Investisseurs :** Répertoires pour ajouter et gérer les informations personnelles et les parts de chaque membre de l'équipe.

---

## ⚙️ 5. Menu : Système

- **Taux de Change :** Gère la conversion entre devises (ex: USD vs devise locale). Pensez à les mettre à jour régulièrement pour que les tableaux de bord affichent des cumuls précis.
- **Rapports :** Permet d'exporter les statistiques en PDF ou d'étudier les chiffres par jour, mois, ou année.
- **Paramètres :** Configure le pourcentage des réserves automatiques (ex: couper 10% des bénéfices pour le fond de roulement), ou les configurations globales du site.

---

## 💡 Le Cycle Idéal (Best Practices)

1. **Le Matin :** L'Admin attribue de l'argent aux agents via **Allocations Agents**.
2. **La Journée :** Les agents travaillent et génèrent des **Opérations** et des **Commissions**.
3. **Pendant le mois :** L'Admin enregistre les **Dépenses** de fonctionnement ("On a acheté du crédit internet").
4. **Fin du Mois :** L'Admin va sur le **Tableau de Bord Paie**. Il regarde le Bénéfice Net restant, clique sur "Calculer Salaires", puis s'il le veut, retire sa part via un **Retrait Bénéfice**.

**Rapid Cash** centralise tout. La confiance n'exclut pas le contrôle !
