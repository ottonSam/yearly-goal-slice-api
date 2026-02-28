from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from wallets.models import Wallet
from wallets.services.wallet import compute_wallet_remaining_limits


class WalletReadSerializer(serializers.ModelSerializer):
    user = serializers.UUIDField(read_only=True, source='user_id', help_text='Wallet owner user ID.')
    remaining_total_limit = serializers.SerializerMethodField(
        help_text='Wallet remaining total limit (wallet limit - current cycle spent - future cycles spent).'
    )
    remaining_cycle_limit = serializers.SerializerMethodField(
        help_text='Current cycle remaining limit (current cycle limit - current cycle spent).'
    )

    def _get_wallet_limit_snapshot(self, wallet: Wallet):
        cache = getattr(self, '_wallet_limit_snapshot_cache', None)
        if cache is None:
            cache = {}
            self._wallet_limit_snapshot_cache = cache

        snapshot = cache.get(wallet.id)
        if snapshot is None:
            snapshot = compute_wallet_remaining_limits(wallet=wallet, reference_date=timezone.localdate())
            cache[wallet.id] = snapshot
        return snapshot

    def get_remaining_total_limit(self, obj):
        return self._get_wallet_limit_snapshot(obj).remaining_total_limit

    def get_remaining_cycle_limit(self, obj):
        return self._get_wallet_limit_snapshot(obj).remaining_cycle_limit

    class Meta:
        model = Wallet
        fields = (
            'id',
            'user',
            'name',
            'limit',
            'cycle_limit_default',
            'remaining_total_limit',
            'remaining_cycle_limit',
            'cycle_starts',
            'cycle_ends',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class WalletCreateUpdateSerializer(serializers.ModelSerializer):
    user = serializers.UUIDField(read_only=True, source='user_id', help_text='Wallet owner user ID.')
    name = serializers.CharField(
        max_length=80,
        required=True,
        help_text='Wallet/project name. Must be unique per user.',
    )
    limit = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        help_text='Wallet total limit. Must be greater than zero and greater than or equal to cycle default limit.',
    )
    cycle_limit_default = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        help_text='Default limit for each monthly cycle. Must be greater than zero.',
    )
    cycle_starts = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=31,
        error_messages={
            'min_value': 'Cycle start day must be between 1 and 31.',
            'max_value': 'Cycle start day must be between 1 and 31.',
        },
        help_text='Day of month when cycle starts (1 to 31).',
    )
    cycle_ends = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=31,
        error_messages={
            'min_value': 'Cycle end day must be between 1 and 31.',
            'max_value': 'Cycle end day must be between 1 and 31.',
        },
        help_text='Day of month when cycle ends (1 to 31). Month-wrapping cycles are allowed.',
    )

    class Meta:
        model = Wallet
        fields = (
            'id',
            'user',
            'name',
            'limit',
            'cycle_limit_default',
            'cycle_starts',
            'cycle_ends',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'active', 'created_at', 'updated_at')

    def validate_name(self, value):
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError('Wallet name cannot be empty.')

        request = self.context.get('request')
        user = request.user if request else None
        if user:
            qs = Wallet.objects.filter(user=user, name__iexact=normalized, active=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('You already have an active wallet with this name.')

        return normalized

    def validate_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError('Wallet limit must be greater than zero.')
        return value

    def validate_cycle_limit_default(self, value):
        if value <= 0:
            raise serializers.ValidationError('Cycle default limit must be greater than zero.')
        return value

    def validate_cycle_starts(self, value):
        if value < 1 or value > 31:
            raise serializers.ValidationError('Cycle start day must be between 1 and 31.')
        return value

    def validate_cycle_ends(self, value):
        if value < 1 or value > 31:
            raise serializers.ValidationError('Cycle end day must be between 1 and 31.')
        return value

    def validate(self, attrs):
        limit = attrs.get('limit')
        cycle_limit_default = attrs.get('cycle_limit_default')
        cycle_starts = attrs.get('cycle_starts')
        cycle_ends = attrs.get('cycle_ends')

        if self.instance:
            if limit is None:
                limit = self.instance.limit
            if cycle_limit_default is None:
                cycle_limit_default = self.instance.cycle_limit_default
            if cycle_starts is None:
                cycle_starts = self.instance.cycle_starts
            if cycle_ends is None:
                cycle_ends = self.instance.cycle_ends

        if limit is not None and cycle_limit_default is not None and limit < cycle_limit_default:
            raise serializers.ValidationError(
                {'limit': 'Wallet limit must be greater than or equal to cycle default limit.'}
            )

        if cycle_starts is not None and cycle_ends is not None and cycle_starts == cycle_ends:
            raise serializers.ValidationError(
                {'cycle_ends': 'Cycle end day must be different from cycle start day.'}
            )

        # Additional guard to prevent invalid numeric values in partial payloads.
        if limit is not None and limit < Decimal('0.01'):
            raise serializers.ValidationError({'limit': 'Wallet limit must be greater than zero.'})
        if cycle_limit_default is not None and cycle_limit_default < Decimal('0.01'):
            raise serializers.ValidationError(
                {'cycle_limit_default': 'Cycle default limit must be greater than zero.'}
            )

        return attrs
