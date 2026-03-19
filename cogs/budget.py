"""Budget tracking and split calculation cog."""

import json
import logging
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_BUDGET
from database import get_db

log = logging.getLogger(__name__)


def _calculate_settlements(expenses: list[dict]) -> list[dict]:
    """Calculate minimum transfers to settle all debts.

    Returns list of {"from": user, "to": user, "amount": float}.
    """
    balances: dict[str, float] = defaultdict(float)

    for exp in expenses:
        paid_by = exp["paid_by"]
        amount = exp["amount"]
        split_among = json.loads(exp["split_among"])
        share = amount / len(split_among)

        balances[paid_by] += amount
        for user in split_among:
            balances[user] -= share

    # Separate debtors and creditors
    debtors = []   # owe money (negative balance)
    creditors = [] # are owed money (positive balance)

    for user, balance in balances.items():
        if balance < -0.01:
            debtors.append([user, -balance])
        elif balance > 0.01:
            creditors.append([user, balance])

    # Greedy settlement
    settlements = []
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][1], creditors[j][1])
        if amount > 0.01:
            settlements.append({
                "from": debtors[i][0],
                "to": creditors[j][0],
                "amount": round(amount),
            })
        debtors[i][1] -= amount
        creditors[j][1] -= amount
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return settlements


class BudgetCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="expense", description="経費を登録")
    @app_commands.describe(
        description="内容 (例: ホテル代)",
        amount="金額 (JPY)",
        paid_by="立替者 (@メンション)",
        split_with="割り勘メンバー (@メンション、カンマ区切り。空=全員)",
        category="カテゴリ: flight / hotel / food / activity / transport / other",
    )
    async def expense(
        self,
        interaction: discord.Interaction,
        description: str,
        amount: float,
        paid_by: discord.Member,
        split_with: str = "",
        category: str = "other",
    ):
        # Parse split members
        if split_with:
            # Extract user IDs from mentions
            member_ids = [
                m.strip().strip("<@!>")
                for m in split_with.split(",")
                if m.strip()
            ]
        else:
            # Default: split among all guild members with a specific role or just use mention
            member_ids = [str(paid_by.id)]  # fallback
            # In practice, list all 7 trip members
            # For now, just split with the payer as placeholder

        # Ensure payer is included
        payer_id = str(paid_by.id)
        if payer_id not in member_ids:
            member_ids.append(payer_id)

        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO expenses (description, amount, currency, paid_by, split_among, category)
                   VALUES (?, ?, 'JPY', ?, ?, ?)""",
                (description, amount, payer_id, json.dumps(member_ids), category),
            )
            await db.commit()

            share = amount / len(member_ids)
            embed = discord.Embed(
                title=f"💸 {description}",
                colour=COLOUR_BUDGET,
            )
            embed.add_field(name="💰 合計", value=f"¥{amount:,.0f}", inline=True)
            embed.add_field(name="👤 立替", value=paid_by.mention, inline=True)
            embed.add_field(name="👥 人数", value=f"{len(member_ids)}人", inline=True)
            embed.add_field(name="💴 1人あたり", value=f"¥{share:,.0f}", inline=True)
            embed.add_field(name="カテゴリ", value=category, inline=True)

            await interaction.response.send_message(embed=embed)
        finally:
            await db.close()

    @app_commands.command(name="budget", description="経費サマリーと精算計算")
    async def budget(self, interaction: discord.Interaction):
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM expenses ORDER BY created_at")
            expenses = await cursor.fetchall()

            if not expenses:
                await interaction.response.send_message("まだ経費が登録されていません。`/expense` で追加！")
                return

            # Summary
            total = sum(e["amount"] for e in expenses)
            by_category = defaultdict(float)
            for e in expenses:
                by_category[e["category"] or "other"] += e["amount"]

            embed = discord.Embed(
                title="💰 経費サマリー",
                colour=COLOUR_BUDGET,
            )
            embed.add_field(
                name="合計",
                value=f"¥{total:,.0f}",
                inline=False,
            )

            cat_emoji = {
                "flight": "✈️", "hotel": "🏨", "food": "🍽️",
                "activity": "🏄", "transport": "🚗", "other": "📦",
            }
            cat_lines = []
            for cat, amt in sorted(by_category.items(), key=lambda x: -x[1]):
                emoji = cat_emoji.get(cat, "📦")
                cat_lines.append(f"{emoji} {cat}: ¥{amt:,.0f}")
            embed.add_field(
                name="カテゴリ別",
                value="\n".join(cat_lines),
                inline=False,
            )

            # Settlements
            expense_dicts = [dict(e) for e in expenses]
            settlements = _calculate_settlements(expense_dicts)

            if settlements:
                settle_lines = []
                for s in settlements:
                    from_user = f"<@{s['from']}>"
                    to_user = f"<@{s['to']}>"
                    settle_lines.append(
                        f"{from_user} → {to_user}: **¥{s['amount']:,}**"
                    )
                embed.add_field(
                    name="💸 精算（最小送金）",
                    value="\n".join(settle_lines),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="💸 精算",
                    value="精算不要（均等です）",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)
        finally:
            await db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(BudgetCog(bot))
