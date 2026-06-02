import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';

// ============================================
// 组件属性类型定义
// ============================================

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

interface InputProps {
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  type?: string;
}

interface CardProps {
  children: React.ReactNode;
  hoverable?: boolean;
  className?: string;
  onClick?: () => void;
}

// ============================================
// 动画配置
// ============================================

const springTransition = {
  type: "spring" as const,
  stiffness: 300,
  damping: 30,
};

const smoothTransition = {
  type: "tween" as const,
  duration: 0.25,
  ease: [0.4, 0, 0.2, 1] as const,
};

// ============================================
// Button 组件
// ============================================

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  className,
  type = 'button',
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2';

  const variantClasses = {
    primary: 'bg-apple-blue text-white hover:bg-apple-blue/90 focus:ring-apple-blue shadow-sm hover:shadow-md',
    secondary: 'bg-apple-ultra-light text-apple-black hover:bg-apple-light-gray focus:ring-apple-gray',
    outline: 'border-2 border-apple-blue text-apple-blue hover:bg-apple-blue hover:text-white focus:ring-apple-blue',
    ghost: 'text-apple-blue hover:bg-apple-blue/10 focus:ring-apple-blue',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const disabledClasses = disabled || loading ? 'opacity-50 cursor-not-allowed' : '';

  return (
    <motion.button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      whileHover={!disabled && !loading ? { scale: 1.02 } : {}}
      whileTap={!disabled && !loading ? { scale: 0.98 } : {}}
      transition={smoothTransition}
      className={clsx(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        disabledClasses,
        className
      )}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4\" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {children}
    </motion.button>
  );
};

// ============================================
// Input 组件
// ============================================

export const Input: React.FC<InputProps> = ({
  label,
  placeholder,
  value,
  onChange,
  error,
  disabled = false,
  className,
  type = 'text',
}) => {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-apple-black mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={onChange}
          disabled={disabled}
          placeholder={placeholder}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={clsx(
            'w-full px-4 py-3 rounded-xl border transition-all duration-200',
            'bg-white text-apple-black placeholder-apple-gray',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            error
              ? 'border-apple-error focus:ring-apple-error/20'
              : 'border-apple-light-gray focus:border-apple-blue focus:ring-apple-blue/20',
            disabled && 'bg-apple-ultra-light cursor-not-allowed',
            className
          )}
          style={{
            boxShadow: error
              ? '0 0 0 3px rgba(255, 59, 48, 0.2)'
              : isFocused
              ? '0 0 0 3px rgba(0, 122, 255, 0.2)'
              : 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
          }}
        />
      </div>
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 text-sm text-apple-error"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
};

// ============================================
// Card 组件
// ============================================

export const Card: React.FC<CardProps> = ({
  children,
  hoverable = false,
  className,
  onClick,
}) => {
  const CardComponent = hoverable ? motion.div : 'div';

  return (
    <CardComponent
      onClick={onClick}
      whileHover={hoverable ? { y: -2, boxShadow: '0 12px 40px rgba(0, 0, 0, 0.12)' } : {}}
      transition={smoothTransition}
      className={clsx(
        'bg-white rounded-2xl p-6',
        hoverable && 'cursor-pointer shadow-sm hover:shadow-lg',
        !hoverable && 'shadow-sm',
        className
      )}
    >
      {children}
    </CardComponent>
  );
};

// ============================================
// 示例页面组件
// ============================================

interface ExamplePageProps {
  title?: string;
  onSubmit?: (data: any) => void;
}

export const ExamplePage: React.FC<ExamplePageProps> = ({
  title = '页面标题',
  onSubmit,
}) => {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!phone || !code) return;
    setLoading(true);
    try {
      onSubmit?.({ phone, code });
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={smoothTransition}
      className="min-h-screen bg-apple-ultra-light p-8"
    >
      <div className="max-w-md mx-auto">
        {/* Header */}
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...smoothTransition, delay: 0.1 }}
          className="text-3xl font-bold text-apple-black mb-2"
          style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif" }}
        >
          {title}
        </motion.h1>

        {/* Card */}
        <Card className="mt-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {/* Phone Input */}
            <Input
              label="手机号"
              placeholder="请输入手机号"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mb-4"
            />

            {/* Code Input */}
            <Input
              label="验证码"
              placeholder="请输入验证码"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="mb-6"
            />

            {/* Submit Button */}
            <Button
              onClick={handleSubmit}
              loading={loading}
              disabled={!phone || !code}
              className="w-full"
              size="lg"
            >
              登录
            </Button>
          </motion.div>
        </Card>
      </div>
    </motion.div>
  );
};

export default ExamplePage;
