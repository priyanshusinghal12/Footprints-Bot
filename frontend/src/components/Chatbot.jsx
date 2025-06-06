import React, { useState, useRef, useEffect } from "react";
import Picker from "emoji-picker-react";
import { motion } from "framer-motion";
import avatar from "../assets/avatar.jpeg";
import logo from "../assets/logo.png";
import { CIcon } from "@coreui/icons-react";
import { cilMicrophone } from "@coreui/icons";

const ChatBot = () => {
	const [messages, setMessages] = useState(() => {
		const saved = localStorage.getItem("chat-history");
		return saved
			? JSON.parse(saved)
			: [
					{
						from: "bot",
						text: "Hi! 👋 Welcome to Footprints Preschool. I’m Arjun, your assistant. May I know your child’s name? 👶",
					},
			  ];
	});

	const sessionId = useRef(null);

	useEffect(() => {
		const saved = localStorage.getItem("session-id");
		if (saved) {
			sessionId.current = saved;
		} else {
			const newId = crypto.randomUUID();
			localStorage.setItem("session-id", newId);
			sessionId.current = newId;
		}
	}, []);

	const [input, setInput] = useState("");
	const [showEmojiPicker, setShowEmojiPicker] = useState(false);
	const [isBotTyping, setIsBotTyping] = useState(false);
	const [isListening, setIsListening] = useState(false);
	const [inputDisabled, setInputDisabled] = useState(false);
	const messagesEndRef = useRef(null);
	const emojiRef = useRef();
	const recognitionRef = useRef(null);

	useEffect(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages]);

	useEffect(() => {
		const handleClickOutside = (event) => {
			if (emojiRef.current && !emojiRef.current.contains(event.target)) {
				setShowEmojiPicker(false);
			}
		};
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	useEffect(() => {
		localStorage.setItem("chat-history", JSON.stringify(messages));
	}, [messages]);

	useEffect(() => {
		if (!("webkitSpeechRecognition" in window)) return;
		const recognition = new window.webkitSpeechRecognition();
		recognition.lang = "en-US";
		recognition.interimResults = false;
		recognition.maxAlternatives = 1;
		recognition.onresult = (event) => {
			const transcript = event.results[0][0].transcript;
			setInput((prev) => prev + " " + transcript);
		};
		recognition.onend = () => setIsListening(false);
		recognition.onerror = () => setIsListening(false);
		recognitionRef.current = recognition;
	}, []);

	const startListening = () => {
		if (recognitionRef.current) {
			setIsListening(true);
			recognitionRef.current.start();
		}
	};

	const handleEmojiClick = (emojiData) => {
		setInput((prev) => prev + emojiData.emoji);
	};

	const clearChat = () => {
		localStorage.removeItem("chat-history");
		setMessages([
			{
				from: "bot",
				text: "Hi! 👋 Welcome to Footprints Preschool. I’m Arjun, your assistant. May I know your child’s name? 👶",
			},
		]);
	};

	const sendMessage = async () => {
		if (!input.trim()) return;
		const userMsg = { from: "user", text: input };
		setMessages((prev) => [...prev, userMsg]);
		setInput("");
		setShowEmojiPicker(false);
		setInputDisabled(true);

		await new Promise((r) => setTimeout(r, 2000));
		setIsBotTyping(true);

		try {
			const res = await fetch("https://footprints-bot.onrender.com/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ message: input, session_id: sessionId.current }),
			});

			const data = await res.json();

			await new Promise((r) => setTimeout(r, 800));
			setMessages((prev) => [...prev, { from: "bot", text: data.response }]);
		} catch {
			setMessages((prev) => [
				...prev,
				{ from: "bot", text: "Oops! Something went wrong." },
			]);
		} finally {
			setIsBotTyping(false);
			setInputDisabled(false);
		}
	};

	return (
		<div className="w-full max-w-2xl h-screen sm:h-[90vh] mx-auto flex flex-col rounded-none sm:rounded-2xl shadow-xl overflow-hidden border border-gray-200 bg-white relative">
			{/* Header */}
			<div className="bg-[#00A9C1] text-white py-4 px-6 text-lg sm:text-xl font-bold flex items-center justify-between">
				<div className="flex items-center gap-2">
					<img
						src={avatar}
						alt="Logo"
						className="h-5 w-5 object-contain rounded-full bg-white p-1 shadow"
					/>
					<span className="ml-2">Footprints Parent Assistant</span>
				</div>
				<button
					onClick={clearChat}
					className="text-xs sm:text-sm bg-white text-[#00A9C1] border border-white hover:border-[#00A9C1] px-3 py-1 rounded-full transition">
					Clear Chat
				</button>
			</div>

			{/* Chat Window */}
			<div className="flex-1 overflow-y-auto px-4 py-5 bg-gray-50 space-y-4">
				{messages.map((msg, idx) => (
					<motion.div
						key={idx}
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.3 }}
						className={`flex ${msg.from === "bot" ? "" : "justify-end"}`}>
						{msg.from === "bot" && (
							<img
								src={logo}
								alt="Bot"
								className="w-8 h-8 rounded-full object-cover mr-2 self-end"
							/>
						)}
						<div
							className={`px-4 py-2 rounded-xl max-w-[80%] whitespace-pre-wrap text-sm leading-relaxed ${
								msg.from === "bot"
									? "bg-cyan-100 text-gray-800"
									: "bg-[#00A9C1] text-white"
							}`}>
							{msg.text.split("\n").map((line, i) => (
								<p key={i} className="mb-1">
									{line.trim()}
								</p>
							))}
						</div>
					</motion.div>
				))}

				{isBotTyping && (
					<div className="flex items-start space-x-2">
						<img
							src={avatar}
							alt="Logo"
							className="h-20 w-20 object-contain rounded-full bg-white p-1 shadow"
						/>
						<div className="bg-cyan-100 text-gray-800 px-4 py-2 rounded-xl text-sm animate-pulse">
							Arjun is typing...
						</div>
					</div>
				)}

				<div ref={messagesEndRef} />
			</div>

			{/* Emoji Picker */}
			{showEmojiPicker && (
				<div ref={emojiRef} className="absolute bottom-20 left-4 z-10">
					<Picker onEmojiClick={handleEmojiClick} height={350} />
				</div>
			)}

			{/* Input Section */}
			<div className="flex items-center border-t p-3 bg-white">
				<button
					onClick={() => setShowEmojiPicker(!showEmojiPicker)}
					className="text-xl text-gray-500 hover:text-[#00A9C1] px-2">
					😊
				</button>
				<input
					type="text"
					value={input}
					disabled={inputDisabled}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={(e) => e.key === "Enter" && sendMessage()}
					placeholder="Type a message to Arjun..."
					className={`flex-grow border border-cyan-200 rounded-full px-4 py-2 focus:outline-none text-gray-700 placeholder-gray-400 mx-2 ${
						inputDisabled ? "bg-gray-100 cursor-not-allowed" : ""
					}`}
				/>
				<button
					onClick={startListening}
					className={`px-2 ${
						isListening ? "text-red-500 animate-pulse" : "text-gray-500"
					}`}
					title="Voice Input">
					<CIcon icon={cilMicrophone} className="w-6 h-6" />
				</button>
				<button
					onClick={sendMessage}
					className="ml-2 p-2 rounded-full bg-[#00A9C1] hover:bg-[#008ba0] transition">
					<img
						src="https://cdn-icons-png.flaticon.com/512/724/724927.png"
						alt="send"
						className="w-4 h-4"
					/>
				</button>
			</div>
		</div>
	);
};

export default ChatBot;
