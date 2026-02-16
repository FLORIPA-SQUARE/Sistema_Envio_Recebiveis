"""Seed script — populates 4 FIDCs and default users.

Run: python -m app.seed  (from backend/ directory)

Senhas de usuarios: definir via variavel de ambiente ou serao geradas automaticamente.
  SEED_ADMIN_PASSWORD=...  SEED_CAMILA_PASSWORD=...  python -m app.seed
"""

import asyncio
import os
import secrets
import sys
from pathlib import Path

# Ensure backend/ is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.email_layout import EmailLayout
from app.models.fidc import Fidc
from app.models.usuario import Usuario
from app.security import hash_password


def _get_password(env_var: str, user_label: str) -> str:
    """Retorna senha da env var ou gera uma aleatoria."""
    pwd = os.environ.get(env_var)
    if pwd:
        return pwd
    pwd = secrets.token_urlsafe(16)
    print(f"  [!] {env_var} nao definida — senha gerada para {user_label}: {pwd}")
    return pwd


FIDCS_SEED = [
    {
        "nome": "CAPITAL",
        "nome_completo": "CAPITAL RS FIDC NP MULTISSETORIAL",
        "cnpj": "12.910.463/0001-70",
        "cc_emails": ["adm@jotajota.net.br"],
        "palavras_chave": ["CAPITAL RS", "CAPITAL RS FIDC"],
        "cor": "#0e639c",
    },
    {
        "nome": "NOVAX",
        "nome_completo": "Novax Fundo de Investimento em Direitos Creditórios",
        "cnpj": "28.879.551/0001-96",
        "cc_emails": ["adm@jotajota.net.br", "controladoria@novaxfidc.com.br"],
        "palavras_chave": ["NOVAX"],
        "cor": "#107c10",
    },
    {
        "nome": "CREDVALE",
        "nome_completo": "CREDVALE FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS MULTISSETORIAL",
        "cnpj": "",
        "cc_emails": ["adm@jotajota.net.br", "nichole@credvalefidc.com.br"],
        "palavras_chave": ["CREDVALE", "CREDIT VALLEY"],
        "cor": "#d83b01",
    },
    {
        "nome": "SQUID",
        "nome_completo": "SQUID FUNDO DE INVESTIMENTO EM DIREITOS CREDITORIOS",
        "cnpj": "",
        "cc_emails": ["adm@jotajota.net.br"],
        "palavras_chave": ["SQUID"],
        "cor": "#8764b8",
    },
]

USERS_SEED = [
    {
        "nome": "Administrador",
        "email": "admin@jotajota.net.br",
        "env_var": "SEED_ADMIN_PASSWORD",
    },
    {
        "nome": "Camila",
        "email": "camila@jotajota.net.br",
        "env_var": "SEED_CAMILA_PASSWORD",
    },
]


async def seed():
    async with async_session() as session:
        # Seed FIDCs
        for fidc_data in FIDCS_SEED:
            result = await session.execute(select(Fidc).where(Fidc.nome == fidc_data["nome"]))
            existing = result.scalar_one_or_none()
            if not existing:
                session.add(Fidc(**fidc_data))
                print(f"  [+] FIDC criado: {fidc_data['nome']}")
            else:
                print(f"  [=] FIDC já existe: {fidc_data['nome']}")

        # Seed users
        for user_data in USERS_SEED:
            result = await session.execute(select(Usuario).where(Usuario.email == user_data["email"]))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                senha = _get_password(user_data["env_var"], user_data["email"])
                session.add(
                    Usuario(
                        nome=user_data["nome"],
                        email=user_data["email"],
                        senha_hash=hash_password(senha),
                    )
                )
                print(f"  [+] Usuário criado: {user_data['email']}")
            else:
                print(f"  [=] Usuário já existe: {user_data['email']}")

        # Seed default email layout
        result = await session.execute(select(EmailLayout).where(EmailLayout.nome == "Padrao"))
        existing_layout = result.scalar_one_or_none()
        if not existing_layout:
            session.add(
                EmailLayout(
                    nome="Padrao",
                    saudacao="Boa tarde,",
                    introducao="Prezado cliente,",
                    mensagem_fechamento="Em caso de duvidas, nossa equipe permanece a disposicao para esclarecimentos.",
                    assinatura_nome="Equipe de Cobranca",
                    ativo=True,
                )
            )
            print("  [+] Email layout criado: Padrao")
        else:
            print("  [=] Email layout ja existe: Padrao")

        await session.commit()
        print("\nSeed concluido!")


if __name__ == "__main__":
    asyncio.run(seed())
