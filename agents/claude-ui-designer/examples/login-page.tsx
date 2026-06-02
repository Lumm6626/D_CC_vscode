import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';

// ============================================
// 登录页面组件
// ============================================

interface LoginPageProps {
  onLogin?: (data: { phone: string; code: string }) => void;
  onGoBack?: () => void;
}

interface FormErrors {
  phone?: string;
  code?: string;
  agreement?: string;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onLogin,
  onGoBack,
}) => {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // 倒计时逻辑
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  // 验证手机号
  const validatePhone = (value: string): string | undefined => {
    if (!value) return '请输入手机号';
    if (!/^1[3-9]\d{9}$/.test(value)) return '请输入正确的手机号';
    return undefined;
  };

  // 验证验证码
  const validateCode = (value: string): string | undefined => {
    if (!value) return '请输入验证码';
    if (value.length !== 6) return '验证码为6位数字';
    return undefined;
  };

  // 获取验证码
  const handleGetCode = () => {
    const phoneError = validatePhone(phone);
    if (phoneError) {
      setErrors(prev => ({ ...prev, phone: phoneError }));
      setTouched(prev => ({ ...prev, phone: true }));
      return;
    }
    // 模拟发送验证码
    setCountdown(60);
  };

  // 提交表单
  const handleSubmit = async () => {
    // 验证表单
    const phoneError = validatePhone(phone);
    const codeError = validateCode(code);

    setTouched({ phone: true, code: true });
    setErrors({
      phone: phoneError,
      code: codeError,
      agreement: agreed ? undefined : '请先阅读并同意用户协议',
    });

    if (phoneError || codeError || !agreed) return;

    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      onLogin?.({ phone, code });
    } finally {
      setLoading(false);
    }
  };

  // 输入框失去焦点时验证
  const handleBlur = (field: string) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    if (field === 'phone') setErrors(prev => ({ ...prev, phone: validatePhone(phone) }));
    if (field === 'code') setErrors(prev => ({ ...prev, code: validateCode(code) }));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="min-h-screen bg-[#F5F5F7] flex flex-col"
    >
      {/* 顶部导航 */}
      <div className="px-4 py-4 flex items-center">
        <button
          onClick={onGoBack}
          className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-[#E8E8ED] transition-colors"
        >
          <svg className="w-6 h-6 text-[#007AFF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* 主内容 */}
      <div className="flex-1 px-6 pb-12">
        {/* 标题 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease: [0, 0, 0.2, 1] }}
        >
          <h1
            className="text-[30px] font-bold text-[#1D1D1F] mb-2"
            style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif" }}
          >
            手机号登录
          </h1>
          <p className="text-[16px] text-[#86868B]">
            未注册的手机号将自动创建账号
          </p>
        </motion.div>

        {/* 表单卡片 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4, ease: [0, 0, 0.2, 1] }}
          className="bg-white rounded-2xl shadow-sm mt-8 p-6"
        >
          {/* 手机号输入 */}
          <div className="mb-4">
            <label className="block text-[14px] font-medium text-[#1D1D1F] mb-2">
              手机号
            </label>
            <div className="relative">
              <input
                type="tel"
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value.replace(/\D/g, '').slice(0, 11));
                  if (touched.phone) setErrors(prev => ({ ...prev, phone: validatePhone(e.target.value) }));
                }}
                onBlur={() => handleBlur('phone')}
                placeholder="请输入手机号"
                className={clsx(
                  'w-full px-4 py-3.5 rounded-xl border text-[16px] text-[#1D1D1F] placeholder-[#86868B]',
                  'bg-white transition-all duration-200 focus:outline-none',
                  errors.phone && touched.phone
                    ? 'border-[#FF3B30]'
                    : 'border-[#D2D2D7] focus:border-[#007AFF]'
                )}
                style={{
                  boxShadow: touched.phone && errors.phone
                    ? '0 0 0 3px rgba(255, 59, 48, 0.2)'
                    : 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
                }}
              />
            </div>
            <AnimatePresence>
              {touched.phone && errors.phone && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="mt-2 text-[12px] text-[#FF3B30]"
                >
                  {errors.phone}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* 验证码输入 */}
          <div className="mb-6">
            <label className="block text-[14px] font-medium text-[#1D1D1F] mb-2">
              验证码
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value.replace(/\D/g, '').slice(0, 6));
                  if (touched.code) setErrors(prev => ({ ...prev, code: validateCode(e.target.value) }));
                }}
                onBlur={() => handleBlur('code')}
                placeholder="请输入验证码"
                className={clsx(
                  'flex-1 px-4 py-3.5 rounded-xl border text-[16px] text-[#1D1D1F] placeholder-[#86868B]',
                  'bg-white transition-all duration-200 focus:outline-none',
                  errors.code && touched.code
                    ? 'border-[#FF3B30]'
                    : 'border-[#D2D2D7] focus:border-[#007AFF]'
                )}
                style={{
                  boxShadow: touched.code && errors.code
                    ? '0 0 0 3px rgba(255, 59, 48, 0.2)'
                    : 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
                }}
              />
              <motion.button
                type="button"
                onClick={handleGetCode}
                disabled={countdown > 0}
                whileHover={{ scale: countdown > 0 ? 1 : 1.02 }}
                whileTap={{ scale: countdown > 0 ? 1 : 0.98 }}
                className={clsx(
                  'px-4 py-3.5 rounded-xl text-[14px] font-medium transition-all duration-150',
                  countdown > 0
                    ? 'bg-[#F5F5F7] text-[#86868B] cursor-not-allowed'
                    : 'bg-[#F5F5F7] text-[#007AFF] hover:bg-[#E8E8ED]'
                )}
              >
                {countdown > 0 ? `${countdown}s` : '获取验证码'}
              </motion.button>
            </div>
            <AnimatePresence>
              {touched.code && errors.code && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="mt-2 text-[12px] text-[#FF3B30]"
                >
                  {errors.code}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* 用户协议 */}
          <div className="mb-6">
            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={() => {
                  setAgreed(!agreed);
                  if (!agreed) setErrors(prev => ({ ...prev, agreement: undefined }));
                }}
                className={clsx(
                  'mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-150',
                  agreed
                    ? 'bg-[#007AFF] border-[#007AFF]'
                    : 'border-[#D2D2D7] hover:border-[#86868B]'
                )}
              >
                <AnimatePresence>
                  {agreed && (
                    <motion.svg
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0, opacity: 0 }}
                      className="w-3 h-3 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </motion.svg>
                  )}
                </AnimatePresence>
              </button>
              <div className="text-[14px] text-[#86868B] leading-5">
                我已阅读并同意
                <a href="#" className="text-[#007AFF]">《用户协议》</a>
                和
                <a href="#" className="text-[#007AFF]">《隐私政策》</a>
              </div>
            </div>
            <AnimatePresence>
              {errors.agreement && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="mt-2 text-[12px] text-[#FF3B30] ml-8"
                >
                  {errors.agreement}
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          {/* 登录按钮 */}
          <motion.button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.02 }}
            whileTap={{ scale: loading ? 1 : 0.98 }}
            className={clsx(
              'w-full py-4 rounded-xl text-[16px] font-semibold text-white transition-all duration-150',
              'bg-[#007AFF] shadow-sm hover:shadow-md',
              loading || (!phone || !code || !agreed) && 'opacity-50 cursor-not-allowed'
            )}
            style={{
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            }}
          >
            {loading ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
            ) : (
              '登录'
            )}
          </motion.button>
        </motion.div>

        {/* 底部提示 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center text-[12px] text-[#86868B] mt-6"
        >
          登录即表示您同意我们的服务条款和隐私政策
        </motion.p>
      </div>
    </motion.div>
  );
};

export default LoginPage;
