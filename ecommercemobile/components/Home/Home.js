import { Dimensions, SectionList, StyleSheet, Text, View } from "react-native";
import MyStyle from "../../style/MyStyle";
import { useEffect, useState } from "react";
import { Button } from "react-native";
import { TextInput, Title } from "react-native-paper";
import { Colors } from "react-native/Libraries/NewAppScreen";


export const Items = (props) => {
    return <Text> Hello {props.firstName} {props.lastName}! </Text>
}

const Home = () => {
    const [cate, setCate] = useState([]);

    const loadCate = async() => {
        try {
            let res = await fetch("http://127.0.0.1:8000/categories/");
            let data = await res.json();
            console.log("Fetched categories:", data);
            setCate(data);
        } catch (err) {
            console.error("Error fetching categories:", err);
        }
    }
    
    useEffect(() => {
        loadCate();
    }, []);

    return (
        <View>
            {cate.map(c => <Text>{c.name}</Text>)}
        </View>
    );
}

export default Home;